"""
Bittensor on-chain data client.
Queries Finney mainnet directly via bittensor SDK — no API credits needed.
"""

import asyncio
import logging
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Optional

try:
    # Import bittensor FIRST so its logging setup runs before ours.
    # bittensor may reconfigure root handlers or set propagate=False on various loggers;
    # we re-assert our logger below so it always inherits from the root handler.
    import bittensor as bt  # noqa: E402
except Exception as exc:  # noqa: BLE001
    bt = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

logger = logging.getLogger(__name__)
logger.propagate = True  # bittensor import may set propagate=False; undo that

NETWORK = "finney"
BLOCKS_PER_DAY = 7200   # ~12 s per block
BLOCKS_PER_TEMPO = 360  # one epoch (tempo) ≈ 360 blocks; NeuronInfo.emission is per-tempo
_MAX_CONCURRENT = 10        # 10 concurrent chain queries
_METRICS_TIMEOUT = 90.0     # seconds per subnet before giving up

# Explicit thread pool sized well above _MAX_CONCURRENT so timed-out threads
# (which can't be killed) never block new tasks from getting a free worker.
# Default ThreadPoolExecutor on GitHub Actions (2 CPUs) = only 6 workers —
# far too few when slow chain calls pile up as zombies.
_executor = ThreadPoolExecutor(max_workers=64, thread_name_prefix="bt_subnet")

# Lazily initialised so the semaphore is always created inside the running loop
_sem: Optional[asyncio.Semaphore] = None


def _get_sem() -> asyncio.Semaphore:
    global _sem
    if _sem is None:
        _sem = asyncio.Semaphore(_MAX_CONCURRENT)
    return _sem


# Per-thread Subtensor instance (WebSocket stays open between calls)
_local = threading.local()

# In-process identity cache — avoids re-fetching identity for the same
# netuid within a single scoring run (e.g. from mapper + run.py).
# Populated by _fetch_all_identities_sync() (batch query_map) on first call.
_identity_cache: dict[int, "SubnetIdentity"] = {}
_identity_cache_lock = threading.Lock()
_all_identities_fetched = False


def _subtensor():
    if bt is None:
        raise RuntimeError(f"bittensor unavailable: {_IMPORT_ERROR}")
    if not hasattr(_local, "st"):
        _local.st = bt.Subtensor(network=NETWORK)
    return _local.st


def clear_caches() -> None:
    global _all_identities_fetched
    with _identity_cache_lock:
        _identity_cache.clear()
        _all_identities_fetched = False


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SubnetIdentity:
    netuid: int
    name: Optional[str] = None
    github_url: Optional[str] = None
    website: Optional[str] = None


@dataclass
class SubnetMetrics:
    netuid: int
    n_total: int = 0
    yuma_n_total: int = 0
    n_active_7d: int = 0
    total_stake_tao: float = 0.0
    unique_coldkeys: int = 0
    top3_stake_fraction: float = 1.0
    emission_per_block_tao: float = 0.0
    incentive_scores: list[float] = field(default_factory=list)
    n_validators: int = 0
    # dTAO AMM pool data (since Feb 2025)
    tao_in_pool: float = 0.0       # SubnetTAO / 1e9
    alpha_in_pool: float = 0.0     # SubnetAlphaIn / 1e9
    alpha_price_tao: float = 0.0   # tao_in_pool / alpha_in_pool
    coldkey_stakes: list[float] = field(default_factory=list)
    validator_stakes: list[float] = field(default_factory=list)
    validator_weight_matrix: list[list[float]] = field(default_factory=list)
    validator_bond_matrix: list[list[float]] = field(default_factory=list)
    last_update_blocks: list[int] = field(default_factory=list)
    yuma_mask: list[bool] = field(default_factory=list)
    mechanism_ids: list[int] = field(default_factory=list)
    immunity_period: int = 0
    registration_allowed: bool = False
    target_regs_per_interval: int = 0
    min_burn: float = 0.0
    max_burn: float = 0.0
    difficulty: float = 0.0


# ---------------------------------------------------------------------------
# Sync helpers (executed in thread pool via asyncio.to_thread)
# ---------------------------------------------------------------------------

def _fetch_netuids() -> list[int]:
    try:
        st = _subtensor()
        version = getattr(bt, "__version__", "unknown")
        logger.info("Subtensor connected — bt v%s", version)
        result = st.get_all_subnets_netuid()  # bittensor 10.x API (was get_subnets() in 8.x)
        if not result:
            logger.error("get_all_subnets_netuid() returned empty list")
        else:
            logger.info("Found %d subnets on chain", len(result))
        return result or []
    except Exception as exc:
        logger.error("get_all_subnets_netuid failed: %s", exc, exc_info=True)
        return []


def _fetch_current_block() -> int:
    try:
        block = _subtensor().get_current_block()
        logger.info("Current block: %d", block)
        return block
    except Exception as exc:
        logger.error("get_current_block failed: %s", exc, exc_info=True)
        return 0


def _fetch_metrics(netuid: int, current_block: int) -> SubnetMetrics:
    """
    Uses subtensor.metagraph() — bittensor 10.x replacement for neurons_lite().
    Returns a Metagraph object with tensor arrays (S, I, last_update, etc.).
    """
    m = SubnetMetrics(netuid=netuid)
    try:
        st = _subtensor()
        meta = st.metagraph(netuid=netuid)

        n = int(meta.n) if hasattr(meta, "n") else len(getattr(meta, "hotkeys", []))
        m.n_total = n
        if n == 0:
            return m

        # Aggregate stake by coldkey (meta.S is stake per neuron in TAO)
        coldkeys = list(getattr(meta, "coldkeys", []))
        stake_arr = list(getattr(meta, "S", []))
        coldkey_stakes: dict[str, float] = defaultdict(float)
        for i in range(n):
            ck = coldkeys[i] if i < len(coldkeys) else ""
            stake_val = float(stake_arr[i]) if i < len(stake_arr) else 0.0
            coldkey_stakes[ck] += stake_val

        total_stake = sum(coldkey_stakes.values())
        m.total_stake_tao = total_stake
        m.unique_coldkeys = len(coldkey_stakes)
        m.coldkey_stakes = list(coldkey_stakes.values())

        # Top-3 coldkey stake fraction
        if total_stake > 0 and coldkey_stakes:
            top3_stake = sum(sorted(coldkey_stakes.values(), reverse=True)[:3])
            m.top3_stake_fraction = min(top3_stake / total_stake, 1.0)
        else:
            m.top3_stake_fraction = 1.0

        # mechid mask — bittensor v10 supports multi-mechanism subnets.
        # Neurons with mechid=0 use yuma consensus (weight-setting, validators);
        # other mechids (e.g. 1=PoW, 2=custom) don't set weights the same way.
        # We restrict activity/validator metrics to yuma neurons so multi-mechanism
        # subnets aren't penalised for "inactive" non-yuma neurons.
        # If mechids are absent (single-mechanism subnet), include all neurons.
        raw_mechids = list(getattr(meta, "mechanism_ids", None) or
                           getattr(meta, "mechids", None) or [])
        if raw_mechids and len(raw_mechids) == n:
            yuma_mask = [int(mid) == 0 for mid in raw_mechids]
            m.mechanism_ids = [int(mid) for mid in raw_mechids]
        else:
            yuma_mask = [True] * n  # single-mechanism: treat all as yuma
            m.mechanism_ids = [0] * n
        m.yuma_mask = yuma_mask
        m.yuma_n_total = int(sum(1 for flag in yuma_mask if flag))

        # Active neurons (weights set within last 7 days, yuma only)
        cutoff = current_block - 7 * BLOCKS_PER_DAY
        last_update = list(getattr(meta, "last_update", []))
        m.last_update_blocks = [int(v) for v in last_update[:n]]
        m.n_active_7d = int(sum(
            1 for i, lu in enumerate(last_update)
            if i < n and yuma_mask[i] and int(lu) >= cutoff
        ))

        # Incentive scores (all neurons — used for distribution health signal)
        m.incentive_scores = [float(v) for v in getattr(meta, "I", [])]

        # Validator count (yuma neurons only)
        m.n_validators = int(sum(
            1 for i, vp in enumerate(getattr(meta, "validator_permit", []))
            if i < n and yuma_mask[i] and vp
        ))
        validator_stakes: list[float] = []
        for idx, vp in enumerate(getattr(meta, "validator_permit", [])):
            if idx < n and yuma_mask[idx] and vp:
                validator_stakes.append(float(stake_arr[idx]) if idx < len(stake_arr) else 0.0)
        m.validator_stakes = validator_stakes

        weight_rows = getattr(meta, "W", None) or getattr(meta, "weights", None) or []
        for idx, row in enumerate(weight_rows):
            if idx >= n or not yuma_mask[idx]:
                continue
            try:
                values = [float(v) for v in row]
            except TypeError:
                values = []
            if any(values):
                m.validator_weight_matrix.append(values)

        bond_rows = getattr(meta, "B", None) or getattr(meta, "bonds", None) or []
        for idx, row in enumerate(bond_rows):
            if idx >= n or not yuma_mask[idx]:
                continue
            try:
                values = [float(v) for v in row]
            except TypeError:
                values = []
            if any(values):
                m.validator_bond_matrix.append(values)

        try:
            hyper = st.get_subnet_hyperparameters(netuid)
            if hyper is not None:
                m.immunity_period = int(getattr(hyper, "immunity_period", 0) or 0)
                m.registration_allowed = bool(getattr(hyper, "registration_allowed", False))
                m.target_regs_per_interval = int(getattr(hyper, "target_regs_per_interval", 0) or 0)
                m.min_burn = float(getattr(hyper, "min_burn", 0) or 0) / 1e9
                m.max_burn = float(getattr(hyper, "max_burn", 0) or 0) / 1e9
                m.difficulty = float(getattr(hyper, "difficulty", 0) or 0)
        except Exception as exc:
            logger.warning("hyperparameter fetch failed for SN%d: %s", netuid, exc)

        # dTAO AMM pool — fetch FIRST so alpha_price_tao is available for emission conversion.
        # SubnetTAO and SubnetAlphaIn are both stored in rao; /1e9 → TAO / Alpha units.
        try:
            tao_res = st.substrate.query("SubtensorModule", "SubnetTAO", [netuid])
            alpha_res = st.substrate.query("SubtensorModule", "SubnetAlphaIn", [netuid])
            tao_val = float(tao_res.value or 0) / 1e9 if tao_res is not None else 0.0
            alpha_val = float(alpha_res.value or 0) / 1e9 if alpha_res is not None else 0.0
            m.tao_in_pool = tao_val
            m.alpha_in_pool = alpha_val
            if alpha_val > 0:
                m.alpha_price_tao = tao_val / alpha_val
        except Exception as exc:
            logger.warning("dTAO pool fetch failed for SN%d: %s", netuid, exc)

        # Emission per block in TAO.
        # meta.emission[i] = alpha emitted to neuron i per TEMPO (SDK already divides rao /1e9).
        # Convert alpha → TAO via alpha_price_tao, then divide by BLOCKS_PER_TEMPO for per-block.
        # Formula: sum(alpha/tempo) * alpha_price_tao / BLOCKS_PER_TEMPO = TAO/block
        try:
            emission_arr = list(getattr(meta, "emission", []))
            if emission_arr and m.alpha_price_tao > 0:
                total_alpha_per_tempo = sum(float(v) for v in emission_arr)
                if total_alpha_per_tempo > 0:
                    m.emission_per_block_tao = (
                        total_alpha_per_tempo * m.alpha_price_tao / BLOCKS_PER_TEMPO
                    )
        except Exception as exc:
            logger.warning("emission fetch failed for SN%d: %s", netuid, exc)

    except Exception as exc:
        logger.error("metagraph fetch failed for SN%d: %s", netuid, exc)

    return m


def _decode_bytes(val) -> Optional[str]:
    """Substrate often returns strings as byte lists."""
    if val is None:
        return None
    if isinstance(val, (bytes, bytearray)):
        try:
            s = val.decode("utf-8").strip("\x00").strip()
            return s or None
        except Exception:
            return None
    if isinstance(val, list):
        try:
            s = bytes(val).decode("utf-8").strip("\x00").strip()
            return s or None
        except Exception:
            return None
    if isinstance(val, str):
        return val.strip() or None
    return None


def _decode_identity_val(val: dict) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract (name, github_url, website) from a decoded SubnetIdentityOf dict."""
    name = _decode_bytes(val.get("subnet_name") or val.get("name"))
    github_url = _decode_bytes(
        val.get("github_repo") or val.get("github_url") or val.get("github")
    )
    website = _decode_bytes(
        val.get("subnet_url") or val.get("url") or val.get("website")
    )
    return name, github_url, website


def _fetch_all_identities_sync() -> None:
    """
    Batch-fetch ALL subnet identities via query_map (one network call).
    Populates _identity_cache. Thread-safe; subsequent calls are no-ops.
    """
    global _all_identities_fetched
    if _all_identities_fetched:
        return

    with _identity_cache_lock:
        if _all_identities_fetched:
            return

        st = _subtensor()
        fetched_with_name = 0
        fetched_total = 0

        for storage_key in ("SubnetIdentitiesV2", "SubnetIdentities"):
            try:
                identity_map = st.substrate.query_map("SubtensorModule", storage_key)
                logger.warning("query_map(%s) returned type: %s", storage_key, type(identity_map).__name__)
                for netuid_key, val_obj in identity_map:
                    try:
                        netuid = int(netuid_key.value)
                        identity = SubnetIdentity(netuid=netuid)
                        v = val_obj.value if val_obj is not None else None
                        if isinstance(v, dict):
                            identity.name, identity.github_url, identity.website = (
                                _decode_identity_val(v)
                            )
                        elif v is not None:
                            # Unexpected type — log so we can investigate
                            logger.warning(
                                "SubnetIdentity for SN%d unexpected type %s: %r",
                                netuid, type(v).__name__, v,
                            )
                        _identity_cache[netuid] = identity
                        fetched_total += 1
                        if identity.name:
                            fetched_with_name += 1
                    except Exception as exc:
                        logger.warning("Error decoding identity entry: %s", exc)

                logger.info(
                    "Batch identity fetch (%s): %d subnets total, %d with names",
                    storage_key, fetched_total, fetched_with_name,
                )
                break  # success — don't try fallback key
            except Exception as exc:
                logger.warning("query_map(%s) failed: %s — trying fallback", storage_key, exc)

        _all_identities_fetched = True


def _fetch_identity(netuid: int) -> SubnetIdentity:
    """
    Return cached identity for a subnet, or an empty placeholder.

    On-chain SubnetIdentitiesV2 / SubnetIdentities do not exist on the current
    Finney runtime (confirmed via run #42 logs). Names are sourced from Taostats
    in run.py after scores are computed, so this function only needs to avoid
    wasteful chain queries that always fail with "Storage function not found".
    """
    return _identity_cache.get(netuid, SubnetIdentity(netuid=netuid))


# ---------------------------------------------------------------------------
# Public async API
# ---------------------------------------------------------------------------

async def get_all_netuids() -> list[int]:
    async with _get_sem():
        loop = asyncio.get_running_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(_executor, _fetch_netuids),
                timeout=_METRICS_TIMEOUT,
            )
        except Exception as exc:
            logger.error("Failed to fetch netuids: %s", exc)
            return []


async def get_current_block() -> int:
    async with _get_sem():
        loop = asyncio.get_running_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(_executor, _fetch_current_block),
                timeout=_METRICS_TIMEOUT,
            )
        except Exception as exc:
            logger.error("Failed to fetch current block: %s", exc)
            return 0


async def get_subnet_metrics(netuid: int, current_block: int) -> SubnetMetrics:
    async with _get_sem():
        loop = asyncio.get_running_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(_executor, _fetch_metrics, netuid, current_block),
                timeout=_METRICS_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.error("Timeout (%.0fs) fetching metrics for SN%d — skipping", _METRICS_TIMEOUT, netuid)
            return SubnetMetrics(netuid=netuid)
        except Exception as exc:
            logger.error("Error fetching metrics for SN%d: %s", netuid, exc)
            return SubnetMetrics(netuid=netuid)


async def prefetch_all_identities() -> None:
    """
    Batch-fetch all subnet identities in a single query_map call.
    Call once before individual get_subnet_identity() calls for efficiency.
    """
    if _all_identities_fetched:
        return
    async with _get_sem():
        if _all_identities_fetched:
            return
        loop = asyncio.get_running_loop()
        try:
            await asyncio.wait_for(
                loop.run_in_executor(_executor, _fetch_all_identities_sync),
                timeout=120.0,
            )
        except Exception as exc:
            logger.warning("Batch identity prefetch failed: %s", exc)


async def get_subnet_identity(netuid: int) -> SubnetIdentity:
    # If batch fetch hasn't run yet, trigger it now (first call wins, rest wait on lock)
    if not _all_identities_fetched:
        await prefetch_all_identities()

    if netuid in _identity_cache:
        return _identity_cache[netuid]

    # Fallback: individual query (handles subnets registered after batch fetch)
    async with _get_sem():
        if netuid in _identity_cache:
            return _identity_cache[netuid]
        loop = asyncio.get_running_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(_executor, _fetch_identity, netuid),
                timeout=_METRICS_TIMEOUT,
            )
        except Exception as exc:
            logger.warning("Failed to fetch identity for SN%d: %s", netuid, exc)
            result = SubnetIdentity(netuid=netuid)
        _identity_cache[netuid] = result
        return result
