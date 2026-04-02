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
from scorer.database import get_external_data_snapshot_map
from scoring.engine import build_scores
from storage.history import load_recent_analysis_history

logger = logging.getLogger(__name__)

SCORE_VERSION = "v5_investment_framework"


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


def _repo_activity_from_snapshot(snapshot: Optional[dict]) -> Optional[RepoActivitySnapshot]:
    if not snapshot:
        return None
    return RepoActivitySnapshot(
        github_url=snapshot.get("github_url"),
        owner=snapshot.get("owner"),
        repo=snapshot.get("repo"),
        source_status=snapshot.get("source_status") or "unavailable",
        fetched_at=snapshot.get("fetched_at"),
        commits_30d=int(snapshot.get("commits_30d") or 0),
        contributors_30d=int(snapshot.get("contributors_30d") or 0),
        stars=int(snapshot.get("stars") or 0),
        forks=int(snapshot.get("forks") or 0),
        open_issues=int(snapshot.get("open_issues") or 0),
        last_push=snapshot.get("last_push"),
    )


async def _fetch_data(netuid: int, current_block: int, progress: list, external_data_by_netuid: dict[int, dict]) -> _SubnetData:
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

    d.repo_activity = _repo_activity_from_snapshot(external_data_by_netuid.get(netuid))
    return d


def _to_snapshot(d: _SubnetData, current_block: int, history: list) -> RawSubnetSnapshot:
    m = d.metrics or SubnetMetrics(netuid=d.netuid)
    return RawSubnetSnapshot(
        netuid=d.netuid,
        current_block=current_block,
        n_total=m.n_total,
        yuma_neurons=m.yuma_n_total or m.n_total,
        active_neurons_7d=m.n_active_7d,
        active_validators_7d=m.n_active_validators_7d if m.n_validators > 0 else None,
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
    is_root = snapshot.netuid == 0
    return {
        "label": "Root Infrastructure" if is_root else artifacts.label,
        "thesis": (
            "Root subnet metrics are reported for context only and excluded from investable opportunity rankings."
            if is_root else artifacts.thesis
        ),
        "investable": not is_root,
        "special_case": "root_subnet" if is_root else None,
        "analysis": artifacts.explanation,
        "primary_outputs": {
            "fundamental_quality": round(artifacts.primary.fundamental_quality * 100, 2),
            "mispricing_signal": round(artifacts.primary.mispricing_signal * 100, 2),
            "fragility_risk": round(artifacts.primary.fragility_risk * 100, 2),
            "signal_confidence": round(artifacts.primary.signal_confidence * 100, 2),
        },
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
    return ScoreBreakdown(
        capital_score=round(artifacts.primary.fundamental_quality * 30, 2),
        activity_score=round(artifacts.primary.mispricing_signal * 25, 2),
        efficiency_score=round((1.0 - artifacts.primary.fragility_risk) * 20, 2),
        health_score=round(artifacts.primary.signal_confidence * 15, 2),
        dev_score=round(max(0.0, min(1.0, 1.0 - artifacts.primary.fragility_risk + artifacts.primary.mispricing_signal - 0.5)) * 10, 2),
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
    external_data_by_netuid = get_external_data_snapshot_map()
    progress = [0, len(netuids)]
    results = await asyncio.gather(
        *[_fetch_data(netuid, current_block, progress, external_data_by_netuid) for netuid in netuids],
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

    investable_scores = sorted(
        [score for score in scores if score.analysis.get("investable", True)],
        key=lambda s: s.score,
        reverse=True,
    )
    for index, score in enumerate(investable_scores, start=1):
        score.rank = index
    return scores
