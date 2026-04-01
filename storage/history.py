from collections import defaultdict

from collectors.models import HistoricalFeaturePoint
from scorer.database import SessionLocal, SubnetScoreRow
from sqlalchemy import desc, select


def load_recent_analysis_history(netuids: list[int]) -> dict[int, list[HistoricalFeaturePoint]]:
    if not netuids:
        return {}
    history: dict[int, list[HistoricalFeaturePoint]] = defaultdict(list)
    with SessionLocal() as session:
        rows = session.execute(
            select(SubnetScoreRow)
            .where(SubnetScoreRow.netuid.in_(netuids))
            .order_by(SubnetScoreRow.netuid, desc(SubnetScoreRow.computed_at))
        ).scalars().all()

    def _pct_to_unit(value):
        if value is None:
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        return numeric / 100.0 if numeric > 1.0 else numeric

    for row in rows:
        raw = row.raw_data if isinstance(row.raw_data, dict) else {}
        analysis = raw.get("analysis", {})
        raw_metrics = raw.get("raw_metrics", {})
        history[row.netuid].append(
            HistoricalFeaturePoint(
                timestamp=row.computed_at.isoformat() if row.computed_at else "",
                alpha_price_tao=row.alpha_price_tao,
                tao_in_pool=row.tao_in_pool,
                emission_per_block_tao=raw_metrics.get("emission_per_block_tao"),
                active_ratio=raw_metrics.get("active_ratio"),
                participation_breadth=raw_metrics.get("participation_breadth"),
                validator_participation=raw_metrics.get("validator_participation"),
                incentive_distribution_quality=raw_metrics.get("incentive_distribution_quality"),
                concentration_proxy=raw_metrics.get("performance_driven_by_few_actors"),
                liquidity_thinness=raw_metrics.get("liquidity_thinness"),
                market_relevance_proxy=raw_metrics.get("market_relevance_proxy"),
                market_structure_floor=raw_metrics.get("market_structure_floor"),
                intrinsic_quality=_pct_to_unit((analysis.get("component_scores", {}) or {}).get("intrinsic_quality")),
                economic_sustainability=_pct_to_unit((analysis.get("component_scores", {}) or {}).get("economic_sustainability")),
                reflexivity=_pct_to_unit((analysis.get("component_scores", {}) or {}).get("reflexivity")),
                stress_robustness=_pct_to_unit((analysis.get("component_scores", {}) or {}).get("stress_robustness")),
                opportunity_gap=_pct_to_unit((analysis.get("component_scores", {}) or {}).get("opportunity_gap")),
                fundamental_quality=_pct_to_unit((analysis.get("primary_outputs", {}) or {}).get("fundamental_quality")),
                mispricing_signal=_pct_to_unit((analysis.get("primary_outputs", {}) or {}).get("mispricing_signal")),
                fragility_risk=_pct_to_unit((analysis.get("primary_outputs", {}) or {}).get("fragility_risk")),
                signal_confidence=_pct_to_unit((analysis.get("primary_outputs", {}) or {}).get("signal_confidence")),
            )
        )
    for points in history.values():
        points.reverse()
    return history
