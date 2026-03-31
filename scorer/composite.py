"""
Composite scorer - signal separation engine for Bittensor subnets.

The old implementation was a percentile dashboard. This version keeps the
existing entrypoints but routes scoring through a 5-axis model:
intrinsic quality, economic sustainability, reflexivity, stress robustness,
and opportunity gap.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from collectors.models import RawSubnetSnapshot, RepoActivitySnapshot
from scorer.bittensor_client import SubnetMetrics, get_all_netuids, get_current_block, get_subnet_metrics
from scorer.github_client import get_commits_last_30d, get_repo_stats
from scorer.subnet_github_mapper import get_github_coords
from scoring.engine import build_scores
from storage.history import load_recent_analysis_history

logger = logging.getLogger(__name__)

SCORE_VERSION = "v4_signal_separation"


class ScoreBreakdown(BaseModel):
    capital_score: float
    activity_score: float
    efficiency_score: float
    health_score: float
    dev_score: float


class SubnetScore(BaseModel):
    netuid: int
    score: float
    breakdown: ScoreBreakdown
    rank: Optional[int] = None
    timestamp: str
    version: str = SCORE_VERSION
    alpha_price_tao: float = 0.0
    tao_in_pool: float = 0.0
    market_cap_tao: float = 0.0
    staking_apy: float = 0.0
    analysis: dict = Field(default_factory=dict)


class _SubnetData:
    def __init__(self, netuid: int) -> None:
        self.netuid = netuid
        self.metrics: Optional[SubnetMetrics] = None
        self.repo_activity: Optional[RepoActivitySnapshot] = None


async def _fetch_data(netuid: int, current_block: int, progress: list) -> _SubnetData:
    d = _SubnetData(netuid)
    d.metrics = await get_subnet_metrics(netuid, current_block)

    progress[0] += 1
    m = d.metrics
    if m and m.n_total > 0:
        logger.info(
            "[%d/%d] SN%d OK - neurons=%d yuma=%d stake=%.0f TAO pool=%.2f emission=%.6f",
            progress[0], progress[1], netuid, m.n_total, m.yuma_n_total,
            m.total_stake_tao, m.tao_in_pool, m.emission_per_block_tao,
        )
    else:
        logger.warning("[%d/%d] SN%d - no on-chain data", progress[0], progress[1], netuid)

    coords = await get_github_coords(netuid, live_fetch=True)
    if coords:
        try:
            commits, repo = await asyncio.gather(
                get_commits_last_30d(coords.owner, coords.repo),
                get_repo_stats(coords.owner, coords.repo),
            )
            d.repo_activity = RepoActivitySnapshot(
                commits_30d=commits.commits_30d if commits else 0,
                contributors_30d=commits.unique_contributors_30d if commits else 0,
                stars=repo.stars if repo else 0,
                forks=repo.forks if repo else 0,
                open_issues=repo.open_issues if repo else 0,
                last_push=repo.last_push if repo else None,
            )
        except Exception as exc:
            logger.warning("GitHub fetch failed for SN%d: %s", netuid, exc)
    return d


def _to_snapshot(d: _SubnetData, current_block: int, history: list) -> RawSubnetSnapshot:
    m = d.metrics or SubnetMetrics(netuid=d.netuid)
    return RawSubnetSnapshot(
        netuid=d.netuid,
        current_block=current_block,
        n_total=m.n_total,
        yuma_neurons=m.yuma_n_total or m.n_total,
        active_neurons_7d=m.n_active_7d,
        total_stake_tao=m.total_stake_tao,
        unique_coldkeys=m.unique_coldkeys,
        top3_stake_fraction=m.top3_stake_fraction,
        emission_per_block_tao=m.emission_per_block_tao,
        incentive_scores=m.incentive_scores,
        n_validators=m.n_validators,
        tao_in_pool=m.tao_in_pool,
        alpha_in_pool=m.alpha_in_pool,
        alpha_price_tao=m.alpha_price_tao,
        coldkey_stakes=m.coldkey_stakes,
        validator_stakes=m.validator_stakes,
        validator_weight_matrix=m.validator_weight_matrix,
        validator_bond_matrix=m.validator_bond_matrix,
        last_update_blocks=m.last_update_blocks,
        yuma_mask=m.yuma_mask,
        mechanism_ids=m.mechanism_ids,
        immunity_period=m.immunity_period,
        registration_allowed=m.registration_allowed,
        target_regs_per_interval=m.target_regs_per_interval,
        min_burn=m.min_burn,
        max_burn=m.max_burn,
        difficulty=m.difficulty,
        github=d.repo_activity,
        history=history,
    )


def _analysis_payload(snapshot: RawSubnetSnapshot, artifacts) -> dict:
    return {
        "label": artifacts.label,
        "thesis": artifacts.thesis,
        "analysis": artifacts.explanation,
        "raw_metrics": {
            **artifacts.bundle.raw,
            "emission_per_block_tao": snapshot.emission_per_block_tao,
            "active_ratio": artifacts.bundle.raw.get("active_ratio"),
            "tao_in_pool": snapshot.tao_in_pool,
            "alpha_price_tao": snapshot.alpha_price_tao,
        },
        "categories": {
            name: metric.category for name, metric in artifacts.bundle.metrics.items()
        },
    }


def _legacy_breakdown(artifacts) -> ScoreBreakdown:
    opportunity_norm = max(0.0, min(1.0, 0.5 + artifacts.axes.opportunity_gap / 2.0))
    return ScoreBreakdown(
        capital_score=round(artifacts.axes.intrinsic_quality * 30, 2),
        activity_score=round(artifacts.axes.economic_sustainability * 25, 2),
        efficiency_score=round((1.0 - artifacts.axes.reflexivity) * 20, 2),
        health_score=round(artifacts.axes.stress_robustness * 15, 2),
        dev_score=round(opportunity_norm * 10, 2),
    )


async def compute_score(netuid: int) -> SubnetScore:
    scores = await compute_all_subnets(netuids=[netuid])
    return scores[0]


async def compute_all_subnets(netuids: Optional[list[int]] = None) -> list[SubnetScore]:
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

    try:
        history_by_netuid = load_recent_analysis_history(netuids)
    except Exception as exc:
        logger.warning("Could not load analysis history: %s", exc)
        history_by_netuid = {}

    snapshots = [_to_snapshot(d, current_block, history_by_netuid.get(d.netuid, [])) for d in all_data]
    artifacts_by_netuid = build_scores(snapshots)

    scores: list[SubnetScore] = []
    for snapshot in snapshots:
        artifacts = artifacts_by_netuid[snapshot.netuid]
        pool = snapshot.tao_in_pool
        market_proxy = pool * 2.0
        scores.append(
            SubnetScore(
                netuid=snapshot.netuid,
                score=artifacts.score,
                breakdown=_legacy_breakdown(artifacts),
                timestamp=datetime.now(timezone.utc).isoformat(),
                alpha_price_tao=round(snapshot.alpha_price_tao, 6),
                tao_in_pool=round(pool, 2),
                market_cap_tao=round(market_proxy, 2),
                staking_apy=round(max(0.0, snapshot.emission_per_block_tao * 7200 * 365 / max(pool, 1e-9) * 100) if pool > 0 else 0.0, 2),
                analysis=_analysis_payload(snapshot, artifacts),
            )
        )

    scores.sort(key=lambda s: s.score, reverse=True)
    for index, score in enumerate(scores, start=1):
        score.rank = index
    return scores
