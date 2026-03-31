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
                intrinsic_quality=(analysis.get("component_scores", {}) or {}).get("intrinsic_quality"),
                economic_sustainability=(analysis.get("component_scores", {}) or {}).get("economic_sustainability"),
                reflexivity=(analysis.get("component_scores", {}) or {}).get("reflexivity"),
                stress_robustness=(analysis.get("component_scores", {}) or {}).get("stress_robustness"),
                opportunity_gap=(analysis.get("component_scores", {}) or {}).get("opportunity_gap"),
            )
        )
    for points in history.values():
        points.reverse()
    return history
