"""
Composite scorer — orchestrates all signals into a single SubnetScore.
Data source: bittensor on-chain SDK + CoinGecko (prices) + GitHub (dev activity).
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel

from scorer.bittensor_client import SubnetMetrics, get_all_netuids, get_current_block, get_subnet_metrics
from scorer.coingecko_client import get_tao_price_usd
from scorer.github_client import get_commits_last_30d, get_repo_stats
from scorer.signals import (
    capital_conviction_score,
    development_activity_score,
    distribution_health_score,
    emission_efficiency_score,
    network_activity_score,
)
from scorer.subnet_github_mapper import get_github_coords

logger = logging.getLogger(__name__)

SCORE_VERSION = "v2"

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
    rank: Optional[int] = None     # filled after all scores computed
    timestamp: str
    version: str = SCORE_VERSION


# ---------------------------------------------------------------------------
# Per-subnet data container
# ---------------------------------------------------------------------------

class _SubnetData:
    def __init__(self, netuid: int) -> None:
        self.netuid = netuid
        self.metrics: Optional[SubnetMetrics] = None
        self.commits = None       # from github_client
        self.tao_price_usd: float = 0.0


# ---------------------------------------------------------------------------
# Data fetcher
# ---------------------------------------------------------------------------

async def _fetch_data(netuid: int, current_block: int, tao_price: float) -> _SubnetData:
    d = _SubnetData(netuid)
    d.tao_price_usd = tao_price

    d.metrics = await get_subnet_metrics(netuid, current_block)

    coords = await get_github_coords(netuid)
    if coords:
        try:
            d.commits, _ = await asyncio.gather(
                get_commits_last_30d(coords.owner, coords.repo),
                get_repo_stats(coords.owner, coords.repo),
            )
        except Exception as exc:
            logger.warning("GitHub fetch failed for SN%d: %s", netuid, exc)

    return d


# ---------------------------------------------------------------------------
# Cross-subnet context (for percentile normalisation)
# ---------------------------------------------------------------------------

class _CrossSubnetContext:
    def __init__(self, all_data: list[_SubnetData]) -> None:
        self.stakes_usd: list[Optional[float]] = []
        self.unique_coldkeys: list[Optional[int]] = []
        self.active_ratios: list[Optional[float]] = []
        self.n_validators: list[Optional[int]] = []
        self.stake_per_emission: list[Optional[float]] = []
        self.commits_30d: list[Optional[int]] = []
        self.contributors_30d: list[Optional[int]] = []

        for d in all_data:
            m = d.metrics

            # Capital
            if m and m.total_stake_tao > 0 and d.tao_price_usd > 0:
                self.stakes_usd.append(m.total_stake_tao * d.tao_price_usd)
            else:
                self.stakes_usd.append(None)

            self.unique_coldkeys.append(m.unique_coldkeys if m else None)

            # Activity
            if m and m.n_total > 0:
                self.active_ratios.append(m.n_active_7d / m.n_total)
            else:
                self.active_ratios.append(None)

            self.n_validators.append(m.n_validators if m else None)

            # Efficiency
            if m and m.emission_per_block_tao > 0:
                self.stake_per_emission.append(m.total_stake_tao / m.emission_per_block_tao)
            else:
                self.stake_per_emission.append(None)

            # Dev
            self.commits_30d.append(d.commits.commits_30d if d.commits else None)
            self.contributors_30d.append(
                d.commits.unique_contributors_30d if d.commits else None
            )


# ---------------------------------------------------------------------------
# Single-subnet scorer
# ---------------------------------------------------------------------------

def _score_one(d: _SubnetData, ctx: _CrossSubnetContext) -> SubnetScore:
    m = d.metrics

    # Signal 1: Capital
    stake_usd = (m.total_stake_tao * d.tao_price_usd) if (m and d.tao_price_usd > 0) else None
    cap = capital_conviction_score(
        stake_usd=stake_usd,
        unique_coldkeys=m.unique_coldkeys if m else None,
        all_stakes_usd=ctx.stakes_usd,
        all_unique_coldkeys=ctx.unique_coldkeys,
    )

    # Signal 2: Activity
    active_ratio: Optional[float] = None
    if m and m.n_total > 0:
        active_ratio = m.n_active_7d / m.n_total

    act = network_activity_score(
        active_ratio=active_ratio,
        n_validators=m.n_validators if m else None,
        all_active_ratios=ctx.active_ratios,
        all_n_validators=ctx.n_validators,
    )

    # Signal 3: Efficiency
    stake_per_emission: Optional[float] = None
    if m and m.emission_per_block_tao > 0:
        stake_per_emission = m.total_stake_tao / m.emission_per_block_tao

    eff = emission_efficiency_score(
        stake_per_emission=stake_per_emission,
        all_stake_per_emission=ctx.stake_per_emission,
    )

    # Signal 4: Health
    health = distribution_health_score(
        incentive_scores=m.incentive_scores if m else [],
        top3_stake_percent=m.top3_stake_fraction if m else None,
    )

    # Signal 5: Dev
    dev = development_activity_score(
        commits_30d=d.commits.commits_30d if d.commits else None,
        unique_contributors_30d=d.commits.unique_contributors_30d if d.commits else None,
        all_commits=ctx.commits_30d,
        all_contributors=ctx.contributors_30d,
    )

    composite = (
        cap * _WEIGHTS["capital"]
        + act * _WEIGHTS["activity"]
        + eff * _WEIGHTS["efficiency"]
        + health * _WEIGHTS["health"]
        + dev * _WEIGHTS["dev"]
    )

    return SubnetScore(
        netuid=d.netuid,
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
    """Compute score for a single subnet."""
    scores = await compute_all_subnets(netuids=[netuid])
    return scores[0]


async def compute_all_subnets(netuids: Optional[list[int]] = None) -> list[SubnetScore]:
    """
    Compute scores for all (or a subset of) subnets.

    1. Fetch current block + TAO price in parallel.
    2. Fetch per-subnet on-chain metrics + GitHub data in parallel.
    3. Build cross-subnet context for percentile normalisation.
    4. Score each subnet.
    5. Assign ranks (1 = best).
    """
    # 1. Current block + price
    current_block, tao_price = await asyncio.gather(
        get_current_block(),
        get_tao_price_usd(),
    )
    tao_price = tao_price or 0.0

    # 2. Subnet universe
    if netuids is None:
        netuids = await get_all_netuids()

    if not netuids:
        logger.error("Could not fetch subnet list from chain")
        return []

    logger.info("Fetching data for %d subnets (block=%d, TAO=%.2f)", len(netuids), current_block, tao_price)

    # 3. Parallel per-subnet fetch — return_exceptions so one bad subnet
    # doesn't abort the entire run
    results = await asyncio.gather(
        *[_fetch_data(netuid, current_block, tao_price) for netuid in netuids],
        return_exceptions=True,
    )
    all_data: list[_SubnetData] = []
    for netuid, res in zip(netuids, results):
        if isinstance(res, BaseException):
            logger.error("Unhandled error fetching SN%d: %s", netuid, res)
            all_data.append(_SubnetData(netuid))  # empty placeholder keeps ranking consistent
        else:
            all_data.append(res)

    # 4. Cross-subnet context
    ctx = _CrossSubnetContext(all_data)

    # 5. Score
    scores = [_score_one(d, ctx) for d in all_data]

    # 6. Rank (highest score = rank 1)
    scores.sort(key=lambda s: s.score, reverse=True)
    for i, s in enumerate(scores, start=1):
        s.rank = i

    return scores
