"""
Composite scorer — orchestrates all signals into a single SubnetScore.
Data source: bittensor on-chain SDK (dTAO pools) + GitHub (dev activity).

Score v3 — Investment Intelligence Model
=========================================
score = undervalue(30) + yield_quality(25) + health(25) + dev(20)

undervalue:   Quality / log10(MarketCap) — the P/E ratio for subnets.
              Answers: "Am I buying quality cheap?"
              Degrades gracefully: uses stake as market proxy when no dTAO pool.

yield_quality: APY(capped) + pool_depth + emission_efficiency.
              Answers: "Is the yield real, sustainable, and deep?"
              Only counts APY from pools with >50 TAO (prevents tiny-pool outliers).

health:       Active neurons + validator count + incentive distribution.
              Answers: "Is the network actually working and decentralized?"

dev:          GitHub commits + unique contributors (30d).
              Answers: "Is anyone building this long-term?"
"""

import asyncio
import logging
import math
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel

from scorer.bittensor_client import BLOCKS_PER_DAY, SubnetMetrics, get_all_netuids, get_current_block, get_subnet_metrics
from scorer.github_client import get_commits_last_30d, get_repo_stats
from scorer.normalizer import percentile_rank
from scorer.signals import (
    development_activity_score,
    distribution_health_score,
)
from scorer.subnet_github_mapper import get_github_coords

logger = logging.getLogger(__name__)

SCORE_VERSION = "v3"

# Signal weights (must sum to 100)
_WEIGHTS = {
    "undervalue": 30,   # quality per unit of market cap
    "yield":      25,   # risk-adjusted, deep-pool yield
    "health":     25,   # network activity + decentralisation
    "dev":        20,   # open-source development activity
}

# Minimum pool depth for APY to be considered meaningful
_MIN_POOL_DEPTH_TAO = 50.0
# Cap APY at 500% to prevent tiny-pool outliers from dominating the signal
_MAX_APY_PCT = 500.0


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------

class ScoreBreakdown(BaseModel):
    # v3 field mapping (DB columns kept for backward compat):
    capital_score: float    # = undervalue signal   (max 30)
    activity_score: float   # = yield_quality signal (max 25)
    efficiency_score: float # = health signal        (max 25)
    health_score: float     # = 0 in v3 (collapsed into efficiency_score)
    dev_score: float        # = dev signal           (max 20)


class SubnetScore(BaseModel):
    netuid: int
    score: float                   # 0–100 composite
    breakdown: ScoreBreakdown
    rank: Optional[int] = None
    timestamp: str
    version: str = SCORE_VERSION
    # dTAO market data
    alpha_price_tao: float = 0.0
    tao_in_pool: float = 0.0
    market_cap_tao: float = 0.0
    staking_apy: float = 0.0       # capped at 500%, 0 if pool < 50 TAO


# ---------------------------------------------------------------------------
# Per-subnet data container
# ---------------------------------------------------------------------------

class _SubnetData:
    def __init__(self, netuid: int) -> None:
        self.netuid = netuid
        self.metrics: Optional[SubnetMetrics] = None
        self.commits = None


# ---------------------------------------------------------------------------
# Data fetcher
# ---------------------------------------------------------------------------

async def _fetch_data(netuid: int, current_block: int, progress: list) -> _SubnetData:
    d = _SubnetData(netuid)
    d.metrics = await get_subnet_metrics(netuid, current_block)

    progress[0] += 1
    m = d.metrics
    if m and m.n_total > 0:
        logger.info(
            "[%d/%d] SN%d OK — %d neurons, %.0f TAO staked, pool=%.2f TAO, "
            "emission=%.6f TAO/blk, alpha_price=%.4f",
            progress[0], progress[1], netuid, m.n_total, m.total_stake_tao,
            m.tao_in_pool, m.emission_per_block_tao, m.alpha_price_tao,
        )
    else:
        logger.warning("[%d/%d] SN%d — no on-chain data", progress[0], progress[1], netuid)

    coords = await get_github_coords(netuid, live_fetch=True)
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
        # Signal 1: Undervalue
        self.value_ratios: list[Optional[float]] = []

        # Signal 2: Yield Quality
        self.apys: list[Optional[float]] = []          # capped, min pool enforced
        self.pool_depths: list[Optional[float]] = []
        self.stake_per_emission: list[Optional[float]] = []

        # Signal 3: Health
        self.active_ratios: list[Optional[float]] = []
        self.n_validators: list[Optional[int]] = []

        # Signal 4: Dev
        self.commits_30d: list[Optional[int]] = []
        self.contributors_30d: list[Optional[int]] = []

        for d in all_data:
            m = d.metrics

            # --- Undervalue inputs ---
            activity_raw = m.n_active_7d / m.n_total if (m and m.n_total > 0) else None
            decentral_raw = (1.0 - m.top3_stake_fraction) if m else None

            # Market proxy: prefer deep dTAO pool; fall back to total stake
            if m and m.tao_in_pool >= _MIN_POOL_DEPTH_TAO:
                market_proxy = m.tao_in_pool
            elif m and m.total_stake_tao > 0:
                market_proxy = m.total_stake_tao
            else:
                market_proxy = None

            if activity_raw is not None and decentral_raw is not None and market_proxy:
                quality_raw = 0.6 * activity_raw + 0.4 * decentral_raw
                self.value_ratios.append(quality_raw / max(0.1, math.log10(1 + market_proxy)))
            else:
                self.value_ratios.append(None)

            # --- Yield inputs ---
            # APY only meaningful above pool depth threshold
            if m and m.tao_in_pool >= _MIN_POOL_DEPTH_TAO and m.emission_per_block_tao > 0:
                raw_apy = (m.emission_per_block_tao * BLOCKS_PER_DAY * 365 / m.tao_in_pool) * 100
                self.apys.append(min(raw_apy, _MAX_APY_PCT))
            else:
                self.apys.append(None)

            self.pool_depths.append(m.tao_in_pool if (m and m.tao_in_pool > 0) else None)

            if m and m.emission_per_block_tao > 0:
                self.stake_per_emission.append(m.total_stake_tao / m.emission_per_block_tao)
            else:
                self.stake_per_emission.append(None)

            # --- Health inputs ---
            if m and m.n_total > 0:
                self.active_ratios.append(m.n_active_7d / m.n_total)
            else:
                self.active_ratios.append(None)
            self.n_validators.append(m.n_validators if m else None)

            # --- Dev inputs ---
            self.commits_30d.append(d.commits.commits_30d if d.commits else None)
            self.contributors_30d.append(d.commits.unique_contributors_30d if d.commits else None)


# ---------------------------------------------------------------------------
# Single-subnet scorer
# ---------------------------------------------------------------------------

def _score_one(d: _SubnetData, ctx: _CrossSubnetContext, idx: int) -> SubnetScore:
    m = d.metrics

    # Signal 1: Undervalue (30pts)
    # "How much network quality per unit of market cap?"
    underval = percentile_rank(ctx.value_ratios[idx], ctx.value_ratios)

    # Signal 2: Yield Quality (25pts)
    # "Is the yield real, deep, and efficient?"
    apy_pct   = percentile_rank(ctx.apys[idx], ctx.apys)
    depth_pct = percentile_rank(ctx.pool_depths[idx], ctx.pool_depths)
    eff_pct   = percentile_rank(ctx.stake_per_emission[idx], ctx.stake_per_emission)

    if ctx.apys[idx] is not None:
        # Full signal: APY + pool depth + emission efficiency
        yield_q = 0.40 * apy_pct + 0.35 * depth_pct + 0.25 * eff_pct
    else:
        # No dTAO pool: pool depth proxy + emission efficiency
        yield_q = 0.60 * depth_pct + 0.40 * eff_pct

    # Signal 3: Health (25pts)
    # "Is the network active and decentralised?"
    active_pct = percentile_rank(ctx.active_ratios[idx], ctx.active_ratios)
    val_pct = percentile_rank(
        float(ctx.n_validators[idx]) if ctx.n_validators[idx] is not None else None,
        [float(x) if x is not None else None for x in ctx.n_validators],
    )
    dist_health = distribution_health_score(
        m.incentive_scores if m else [],
        m.top3_stake_fraction if m else None,
    )
    health = 0.40 * active_pct + 0.25 * val_pct + 0.35 * dist_health

    # Signal 4: Development (20pts)
    dev = development_activity_score(
        d.commits.commits_30d if d.commits else None,
        d.commits.unique_contributors_30d if d.commits else None,
        ctx.commits_30d,
        ctx.contributors_30d,
    )

    composite = (
        underval * _WEIGHTS["undervalue"]
        + yield_q * _WEIGHTS["yield"]
        + health  * _WEIGHTS["health"]
        + dev     * _WEIGHTS["dev"]
    )

    # Display values for frontend
    tao_pool    = m.tao_in_pool if m else 0.0
    alpha_price = m.alpha_price_tao if m else 0.0
    market_cap  = tao_pool * 2  # AMM TVL proxy
    display_apy = ctx.apys[idx] or 0.0  # already capped

    return SubnetScore(
        netuid=d.netuid,
        score=round(composite, 2),
        breakdown=ScoreBreakdown(
            capital_score=round(underval * _WEIGHTS["undervalue"], 2),
            activity_score=round(yield_q * _WEIGHTS["yield"], 2),
            efficiency_score=round(health * _WEIGHTS["health"], 2),
            health_score=0.0,
            dev_score=round(dev * _WEIGHTS["dev"], 2),
        ),
        timestamp=datetime.now(timezone.utc).isoformat(),
        alpha_price_tao=round(alpha_price, 6),
        tao_in_pool=round(tao_pool, 2),
        market_cap_tao=round(market_cap, 2),
        staking_apy=display_apy,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def compute_score(netuid: int) -> SubnetScore:
    scores = await compute_all_subnets(netuids=[netuid])
    return scores[0]


async def compute_all_subnets(netuids: Optional[list[int]] = None) -> list[SubnetScore]:
    """
    Compute scores for all (or a subset of) subnets.

    1. Fetch current block.
    2. Fetch per-subnet on-chain metrics + GitHub data in parallel.
    3. Build cross-subnet context for percentile normalisation.
    4. Score each subnet.
    5. Assign ranks (1 = best).
    """
    current_block = await get_current_block()

    if netuids is None:
        netuids = await get_all_netuids()

    if not netuids:
        logger.error("Could not fetch subnet list from chain")
        return []

    logger.info("Fetching data for %d subnets (block=%d)", len(netuids), current_block)
    progress = [0, len(netuids)]

    results = await asyncio.gather(
        *[_fetch_data(netuid, current_block, progress) for netuid in netuids],
        return_exceptions=True,
    )
    all_data: list[_SubnetData] = []
    for netuid, res in zip(netuids, results):
        if isinstance(res, BaseException):
            logger.error("Unhandled error fetching SN%d: %s", netuid, res)
            all_data.append(_SubnetData(netuid))
        else:
            all_data.append(res)

    ctx = _CrossSubnetContext(all_data)
    scores = [_score_one(d, ctx, i) for i, d in enumerate(all_data)]

    scores.sort(key=lambda s: s.score, reverse=True)
    for i, s in enumerate(scores, start=1):
        s.rank = i

    return scores
