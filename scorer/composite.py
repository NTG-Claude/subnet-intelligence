"""
Composite scorer — orchestrates all signals into a single SubnetScore.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel

from scorer.github_client import get_commits_last_30d, get_repo_stats
from scorer.signals import (
    capital_conviction_score,
    development_activity_score,
    distribution_health_score,
    emission_efficiency_score,
    network_activity_score,
)
from scorer.subnet_github_mapper import get_github_coords
from scorer.taostats_client import TaostatsClient

logger = logging.getLogger(__name__)

SCORE_VERSION = "v1"

# Signal weights (must sum to 100)
_WEIGHTS = {
    "capital": 25,
    "activity": 25,
    "efficiency": 20,
    "health": 15,
    "dev": 15,
}


# ---------------------------------------------------------------------------
# Output model
# ---------------------------------------------------------------------------

class ScoreBreakdown(BaseModel):
    capital_score: float
    activity_score: float
    efficiency_score: float
    health_score: float
    dev_score: float


class SubnetScore(BaseModel):
    netuid: int
    score: float                   # 0–100 composite
    breakdown: ScoreBreakdown
    rank: Optional[int] = None     # filled in after all scores are computed
    timestamp: str
    version: str = SCORE_VERSION


# ---------------------------------------------------------------------------
# Raw data container (internal)
# ---------------------------------------------------------------------------

class _RawData:
    def __init__(self, netuid: int) -> None:
        self.netuid = netuid
        # Taostats
        self.subnet_info = None
        self.history = None
        self.metagraph = None
        self.registrations = None
        self.coldkey = None
        self.pool = None
        self.weights = None
        # GitHub
        self.commits = None
        self.repo_stats = None


# ---------------------------------------------------------------------------
# Data fetcher
# ---------------------------------------------------------------------------

async def _fetch_raw(netuid: int) -> _RawData:
    raw = _RawData(netuid)

    async with TaostatsClient() as client:
        (
            raw.subnet_info,
            raw.history,
            raw.metagraph,
            raw.registrations,
            raw.coldkey,
            raw.pool,
            raw.weights,
        ) = await asyncio.gather(
            client.get_all_subnets(),          # we'll filter by netuid below
            client.get_subnet_history(netuid, days=30),
            client.get_metagraph(netuid),
            client.get_neuron_registrations(netuid, days=7),
            client.get_coldkey_distribution(netuid),
            client.get_subnet_pools(netuid),
            client.get_validator_weights(netuid),
        )

    # GitHub
    coords = await get_github_coords(netuid)
    if coords:
        raw.commits, raw.repo_stats = await asyncio.gather(
            get_commits_last_30d(coords.owner, coords.repo),
            get_repo_stats(coords.owner, coords.repo),
        )

    return raw


# ---------------------------------------------------------------------------
# Cross-subnet context (needed for percentile normalisation)
# ---------------------------------------------------------------------------

class _CrossSubnetContext:
    """Holds all-subnet lists needed for percentile ranking."""

    def __init__(self, all_raw: list[_RawData], all_subnets_info: list) -> None:
        total_market_cap = sum(
            s.market_cap_usd for s in all_subnets_info if s.market_cap_usd
        ) or 1.0

        self.flow_ratios: list[Optional[float]] = []
        self.unique_stakers: list[Optional[int]] = []
        self.liquidity: list[Optional[float]] = []
        self.miner_growths: list[Optional[float]] = []
        self.registrations_7d: list[Optional[int]] = []
        self.weight_commits: list[Optional[int]] = []
        self.efficiency_ratios: list[Optional[float]] = []
        self.commits_30d: list[Optional[int]] = []
        self.contributors_30d: list[Optional[int]] = []

        # Build info lookup
        info_by_netuid = {s.netuid: s for s in all_subnets_info}

        for raw in all_raw:
            info = info_by_netuid.get(raw.netuid)

            # --- capital ---
            if info and info.market_cap_usd and info.market_cap_usd > 0 and info.flow_30d is not None:
                self.flow_ratios.append(info.flow_30d / info.market_cap_usd)
            else:
                self.flow_ratios.append(None)

            self.unique_stakers.append(raw.coldkey.unique_coldkeys if raw.coldkey else None)
            self.liquidity.append(raw.pool.liquidity_usd if raw.pool else None)

            # --- activity ---
            if raw.history and len(raw.history) >= 2:
                first = raw.history[-1]
                miner_30d = getattr(first, "miner_count", None)
                miner_now = getattr(raw.history[0], "miner_count", None)
                if miner_now and miner_30d and miner_30d > 0:
                    self.miner_growths.append((miner_now - miner_30d) / miner_30d)
                else:
                    self.miner_growths.append(None)
            else:
                self.miner_growths.append(None)

            self.registrations_7d.append(len(raw.registrations) if raw.registrations else None)
            self.weight_commits.append(
                sum(w.weight_commits or 0 for w in raw.weights) if raw.weights else None
            )

            # --- efficiency ---
            if info and info.emission_percent and info.market_cap_usd:
                mcp = info.market_cap_usd / total_market_cap
                self.efficiency_ratios.append(mcp / info.emission_percent if info.emission_percent > 0 else None)
            else:
                self.efficiency_ratios.append(None)

            # --- dev ---
            self.commits_30d.append(raw.commits.commits_30d if raw.commits else None)
            self.contributors_30d.append(raw.commits.unique_contributors_30d if raw.commits else None)


# ---------------------------------------------------------------------------
# Single-subnet scorer
# ---------------------------------------------------------------------------

def _score_one(raw: _RawData, ctx: _CrossSubnetContext, info_by_netuid: dict) -> SubnetScore:
    info = info_by_netuid.get(raw.netuid)
    total_market_cap = sum(
        s.market_cap_usd for s in info_by_netuid.values() if s.market_cap_usd
    ) or 1.0

    # --- Signal 1: Capital ---
    cap = capital_conviction_score(
        net_flow_30d=info.flow_30d if info else None,
        market_cap_usd=info.market_cap_usd if info else None,
        unique_stakers=raw.coldkey.unique_coldkeys if raw.coldkey else None,
        liquidity_usd=raw.pool.liquidity_usd if raw.pool else None,
        all_flow_ratios=ctx.flow_ratios,
        all_unique_stakers=ctx.unique_stakers,
        all_liquidity=ctx.liquidity,
    )

    # --- Signal 2: Activity ---
    miner_now, miner_30d = None, None
    if raw.history and len(raw.history) >= 2:
        miner_now = getattr(raw.history[0], "miner_count", None)
        miner_30d = getattr(raw.history[-1], "miner_count", None)

    act = network_activity_score(
        miner_count_now=miner_now,
        miner_count_30d_ago=miner_30d,
        new_registrations_7d=len(raw.registrations) if raw.registrations else None,
        weight_commits_per_epoch=sum(w.weight_commits or 0 for w in raw.weights) if raw.weights else None,
        all_miner_growths=ctx.miner_growths,
        all_registrations=ctx.registrations_7d,
        all_weight_commits=ctx.weight_commits,
    )

    # --- Signal 3: Efficiency ---
    market_cap_percent = None
    if info and info.market_cap_usd:
        market_cap_percent = info.market_cap_usd / total_market_cap

    eff = emission_efficiency_score(
        emission_percent=info.emission_percent if info else None,
        market_cap_percent=market_cap_percent,
        all_ratios=ctx.efficiency_ratios,
    )

    # --- Signal 4: Health ---
    incentive_scores = [n.incentive for n in raw.metagraph if n.incentive is not None] if raw.metagraph else []
    health = distribution_health_score(
        incentive_scores=incentive_scores,
        top3_stake_percent=raw.coldkey.top3_stake_percent if raw.coldkey else None,
    )

    # --- Signal 5: Dev ---
    dev = development_activity_score(
        commits_30d=raw.commits.commits_30d if raw.commits else None,
        unique_contributors_30d=raw.commits.unique_contributors_30d if raw.commits else None,
        all_commits=ctx.commits_30d,
        all_contributors=ctx.contributors_30d,
    )

    # Composite (0–100)
    composite = (
        cap * _WEIGHTS["capital"]
        + act * _WEIGHTS["activity"]
        + eff * _WEIGHTS["efficiency"]
        + health * _WEIGHTS["health"]
        + dev * _WEIGHTS["dev"]
    )

    return SubnetScore(
        netuid=raw.netuid,
        score=round(composite, 2),
        breakdown=ScoreBreakdown(
            capital_score=round(cap * _WEIGHTS["capital"], 2),
            activity_score=round(act * _WEIGHTS["activity"], 2),
            efficiency_score=round(eff * _WEIGHTS["efficiency"], 2),
            health_score=round(health * _WEIGHTS["health"], 2),
            dev_score=round(dev * _WEIGHTS["dev"], 2),
        ),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def compute_score(netuid: int) -> SubnetScore:
    """Compute score for a single subnet (fetches its own cross-subnet context)."""
    scores = await compute_all_subnets(netuids=[netuid])
    return scores[0]


async def compute_all_subnets(netuids: Optional[list[int]] = None) -> list[SubnetScore]:
    """
    Compute scores for all (or a subset of) subnets in parallel.

    Steps:
    1. Fetch all-subnet list from Taostats to get the universe.
    2. Fetch per-subnet data in parallel.
    3. Build cross-subnet context for percentile normalisation.
    4. Score each subnet.
    5. Assign ranks (1 = best).
    """
    # 1. Universe
    async with TaostatsClient() as client:
        all_subnets_info = await client.get_all_subnets()

    if not all_subnets_info:
        logger.error("Could not fetch subnet list from Taostats")
        return []

    if netuids is not None:
        target_netuids = netuids
    else:
        target_netuids = [s.netuid for s in all_subnets_info]

    # 2. Parallel per-subnet fetch
    raw_list: list[_RawData] = await asyncio.gather(
        *[_fetch_raw(netuid) for netuid in target_netuids]
    )

    # 3. Cross-subnet context
    ctx = _CrossSubnetContext(raw_list, all_subnets_info)
    info_by_netuid = {s.netuid: s for s in all_subnets_info}

    # 4. Score
    scores = [_score_one(raw, ctx, info_by_netuid) for raw in raw_list]

    # 5. Rank (highest score = rank 1)
    scores.sort(key=lambda s: s.score, reverse=True)
    for i, s in enumerate(scores, start=1):
        s.rank = i

    return scores
