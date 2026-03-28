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

# Module-level cache for get_all_subnets_info() — fetched once per process,
# reused by all _fetch_metrics() calls to avoid 128x redundant chain queries.
_all_subnets_info_cache: list = []
_all_subnets_info_lock = threading.Lock()


def _get_cached_subnets_info() -> list:
    global _all_subnets_info_cache
    if _all_subnets_info_cache:
        return _all_subnets_info_cache
    with _all_subnets_info_lock:
        if _all_subnets_info_cache:
            return _all_subnets_info_cache
        try:
            _all_subnets_info_cache = _subtensor().get_all_subnets_info() or []
            logger.info("Cached info for %d subnets from chain", len(_all_subnets_info_cache))
        except Exception as exc:
            logger.warning("get_all_subnets_info failed: %s", exc)
            _all_subnets_info_cache = []
    return _all_subnets_info_cache


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
        result = st.get_subnets()  # correct name in bittensor 8.x (was get_all_subnet_netuids in older docs)
        if not result:
            logger.error("get_subnets() returned empty list — chain unreachable or no subnets found")
        else:
            logger.info("Found %d subnets on chain", len(result))
        return result or []
    except Exception as exc:
        logger.error("get_subnets failed: %s", exc, exc_info=True)
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
    Uses neurons_lite() — much faster than metagraph() because it skips
    building PyTorch tensor arrays (S, W, B, …) and only fetches lightweight
    NeuronInfoLite records via a single RPC call.
    """
    m = SubnetMetrics(netuid=netuid)
    try:
        st = _subtensor()
        neurons = st.neurons_lite(netuid=netuid)

        m.n_total = len(neurons)

        # Aggregate stake by coldkey
        coldkey_stakes: dict[str, float] = defaultdict(float)
        for n in neurons:
            try:
                stake_val = float(n.total_stake)
            except (TypeError, ValueError):
                stake_val = 0.0
            coldkey_stakes[n.coldkey] += stake_val

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
        m.n_active_7d = int(sum(1 for n in neurons if int(n.last_update) >= cutoff))

        # Incentive scores
        m.incentive_scores = [float(n.incentive) for n in neurons]

        # Validator count
        m.n_validators = int(sum(1 for n in neurons if n.validator_permit))

        # Emission per block in TAO — use cached get_all_subnets_info() result
        try:
            all_info = _get_cached_subnets_info()
            subnet_info = next((s for s in all_info if s.netuid == netuid), None)
            if subnet_info is not None and hasattr(subnet_info, "emission_value"):
                raw = float(subnet_info.emission_value)
                # emission_value is in rao (1 TAO = 1e9 rao) in bittensor 8.x
                m.emission_per_block_tao = raw / 1e9 if raw > 1.0 else raw
        except Exception as exc:
            logger.warning("emission fetch failed for SN%d: %s", netuid, exc)

    except Exception as exc:
        logger.error("neurons_lite fetch failed for SN%d: %s", netuid, exc)

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

        # Fallback: subnet name from cached get_all_subnets_info()
        if identity.name is None:
            try:
                all_info = _get_cached_subnets_info()
                subnet_info = next((s for s in all_info if s.netuid == netuid), None)
                if subnet_info:
                    identity.name = getattr(subnet_info, "subnet_name", None) or getattr(
                        subnet_info, "name", None
                    )
            except Exception:
                pass

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
