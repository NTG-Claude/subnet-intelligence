from statistics import fmean

from features.normalization import clamp01


def build_quality_components(raw: dict[str, float | None], normalized: dict[str, float]) -> dict[str, float]:
    participation_health = clamp01(
        0.45 * normalized.get("active_ratio", 0.0)
        + 0.35 * normalized.get("participation_breadth", 0.0)
        + 0.20 * normalized.get("update_freshness", 0.0)
    )
    validator_health = clamp01(
        0.45 * normalized.get("validator_participation", 0.0)
        + 0.25 * normalized.get("validator_signal_coverage", 0.0)
        + 0.15 * normalized.get("meaningful_discrimination", 0.5)
        + 0.15 * (1.0 - normalized.get("cross_validator_disagreement", 0.5))
    )
    liquidity_health = clamp01(
        0.60 * normalized.get("reserve_depth", 0.0)
        + 0.40 * normalized.get("liquidity_thinness", 0.0)
    )
    concentration_health = clamp01(
        0.65 * (1.0 - normalized.get("concentration", 1.0))
        + 0.35 * normalized.get("participation_breadth", 0.0)
    )
    market_relevance = clamp01(
        0.45 * normalized.get("market_relevance_proxy", 0.0)
        + 0.30 * normalized.get("reserve_depth", 0.0)
        + 0.25 * participation_health
    )
    return {
        "participation_health": participation_health,
        "validator_health": validator_health,
        "liquidity_health": liquidity_health,
        "concentration_health": concentration_health,
        "market_relevance": market_relevance,
        "fundamental_health": clamp01(
            fmean(
                [
                    participation_health,
                    validator_health,
                    liquidity_health,
                    concentration_health,
                    market_relevance,
                ]
            )
        ),
    }
