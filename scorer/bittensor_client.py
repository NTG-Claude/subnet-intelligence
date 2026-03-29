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

logger = logging.getLogger(__name__)

# Eager import so bittensor's logging setup happens before _setup_logging() runs.
# This ensures our handlers (set in run.py) are applied AFTER bittensor's and win.
import bittensor as bt  # noqa: E402

NETWORK = "finney"
BLOCKS_PER_DAY = 7200  # ~12 s per block
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
# netuid within a single scoring run (e.g. from mapper + run.py)
_identity_cache: dict[int, "SubnetIdentity"] = {}

# Module-level cache for EmissionValues — fetched once per process via query_map,
# reused by all _fetch_metrics() calls to avoid 128x redundant chain queries.
# bittensor 10.x removed get_all_subnets_info(); emission lives in
# SubtensorModule.EmissionValues storage (netuid → rao, Compact<u64>).
_emission_cache: dict[int, float] = {}
_emission_cache_lock = threading.Lock()


def _get_cached_emission_values() -> dict[int, float]:
    global _emission_cache
    if _emission_cache:
        return _emission_cache
    with _emission_cache_lock:
        if _emission_cache:
            return _emission_cache
        try:
            result = _subtensor().substrate.query_map("SubtensorModule", "EmissionValues")
            for netuid_key, val in result:
                _emission_cache[int(netuid_key.value)] = float(val.value or 0)
            logger.info("Cached emission values for %d subnets from chain", len(_emission_cache))
        except Exception as exc:
            logger.warning("EmissionValues query_map failed: %s", exc)
    return _emission_cache


def _subtensor():
    if not hasattr(_local, "st"):
        _local.st = bt.Subtensor(network=NETWORK)
    return _local.st


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
    n_active_7d: int = 0
    total_stake_tao: float = 0.0
    unique_coldkeys: int = 0
    top3_stake_fraction: float = 1.0
    emission_per_block_tao: float = 0.0
    incentive_scores: list[float] = field(default_factory=list)
    n_validators: int = 0


# ---------------------------------------------------------------------------
# Sync helpers (executed in thread pool via asyncio.to_thread)
# ---------------------------------------------------------------------------

def _fetch_netuids() -> list[int]:
    try:
        st = _subtensor()
        logger.info("Subtensor connected — bt v%s", bt.__version__)
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

        # Top-3 coldkey stake fraction
        if total_stake > 0 and coldkey_stakes:
            top3_stake = sum(sorted(coldkey_stakes.values(), reverse=True)[:3])
            m.top3_stake_fraction = min(top3_stake / total_stake, 1.0)
        else:
            m.top3_stake_fraction = 1.0

        # Active neurons (weights set within last 7 days)
        cutoff = current_block - 7 * BLOCKS_PER_DAY
        last_update = list(getattr(meta, "last_update", []))
        m.n_active_7d = int(sum(1 for lu in last_update if int(lu) >= cutoff))

        # Incentive scores
        m.incentive_scores = [float(v) for v in getattr(meta, "I", [])]

        # Validator count
        m.n_validators = int(sum(1 for vp in getattr(meta, "validator_permit", []) if vp))

        # Emission per block in TAO — sum of per-neuron emissions already in metagraph.
        # NeuronInfo.emission is stored as n.emission/1e9 (rao→TAO) during decode,
        # so meta.emission array is already in TAO. No extra chain call needed.
        try:
            emission_arr = list(getattr(meta, "emission", []))
            if emission_arr:
                total_tao = sum(float(v) for v in emission_arr)
                if total_tao > 0:
                    m.emission_per_block_tao = total_tao
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


def _fetch_identity(netuid: int) -> SubnetIdentity:
    identity = SubnetIdentity(netuid=netuid)
    try:
        st = _subtensor()
        # Attempt on-chain SubnetIdentities storage
        try:
            result = st.substrate.query("SubtensorModule", "SubnetIdentities", [netuid])
            if result is not None and result.value:
                val = result.value
                if isinstance(val, dict):
                    identity.name = _decode_bytes(val.get("subnet_name") or val.get("name"))
                    identity.github_url = _decode_bytes(
                        val.get("github_url") or val.get("github")
                    )
                    identity.website = _decode_bytes(
                        val.get("url") or val.get("website")
                    )
        except Exception:
            pass  # storage key may not exist

        # Fallback: subnet name from SubtensorModule.SubnetName storage (bittensor 10.x)
        if identity.name is None:
            try:
                result = st.substrate.query("SubtensorModule", "SubnetName", [netuid])
                raw = result.value if result is not None else None
                if netuid == 4:  # debug SN4 (Targon) specifically
                    import sys
                    print(f"[DEBUG] SubnetName SN4: raw={raw!r} type={type(raw).__name__}", flush=True, file=sys.stderr)
                if raw:
                    identity.name = _decode_bytes(raw)
            except Exception as exc:
                if netuid == 4:
                    import sys
                    print(f"[DEBUG] SubnetName SN4 EXCEPTION: {exc!r}", flush=True, file=sys.stderr)

    except Exception as exc:
        logger.warning("identity fetch failed for SN%d: %s", netuid, exc)

    return identity


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


async def get_subnet_identity(netuid: int) -> SubnetIdentity:
    if netuid in _identity_cache:
        return _identity_cache[netuid]
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
