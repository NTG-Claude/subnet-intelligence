"""
Bittensor on-chain data client.
Queries Finney mainnet directly via bittensor SDK — no API credits needed.
"""

import asyncio
import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Eager import so bittensor's logging setup happens before _setup_logging() runs.
# This ensures our handlers (set in run.py) are applied AFTER bittensor's and win.
import bittensor as bt  # noqa: E402

NETWORK = "finney"
BLOCKS_PER_DAY = 7200  # ~12 s per block
_MAX_CONCURRENT = 6

# Lazily initialised so the semaphore is always created inside the running loop
_sem: Optional[asyncio.Semaphore] = None


def _get_sem() -> asyncio.Semaphore:
    global _sem
    if _sem is None:
        _sem = asyncio.Semaphore(_MAX_CONCURRENT)
    return _sem


# Per-thread Subtensor instance (WebSocket stays open between calls)
_local = threading.local()


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
        return _subtensor().get_all_subnet_netuids()
    except Exception as exc:
        logger.error("get_all_subnet_netuids failed: %s", exc)
        return []


def _fetch_current_block() -> int:
    try:
        return _subtensor().get_current_block()
    except Exception as exc:
        logger.error("get_current_block failed: %s", exc)
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

        # Emission per block in TAO
        try:
            subnet_info = st.get_subnet_info(netuid)
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

        # Fallback: subnet name from SubnetInfo
        if identity.name is None:
            try:
                subnet_info = st.get_subnet_info(netuid)
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
        return await asyncio.to_thread(_fetch_netuids)


async def get_current_block() -> int:
    async with _get_sem():
        return await asyncio.to_thread(_fetch_current_block)


async def get_subnet_metrics(netuid: int, current_block: int) -> SubnetMetrics:
    async with _get_sem():
        return await asyncio.to_thread(_fetch_metrics, netuid, current_block)


async def get_subnet_identity(netuid: int) -> SubnetIdentity:
    async with _get_sem():
        return await asyncio.to_thread(_fetch_identity, netuid)
