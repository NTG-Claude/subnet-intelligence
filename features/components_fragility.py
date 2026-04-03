from features.normalization import clamp01


def build_fragility_components(raw: dict[str, float | None], normalized: dict[str, float], base_components: dict[str, float]) -> dict[str, float]:
    crowding_level = clamp01(
        0.48 * normalized.get("crowding_proxy", 0.0)
        + 0.20 * normalized.get("overreaction_score", 0.0)
        + 0.20 * max(normalized.get("market_relevance_proxy", 0.0) - 0.55, 0.0)
        + 0.12 * normalized.get("concentration", 0.0)
    )
    concentration_risk = clamp01(normalized.get("concentration", 0.0))
    thin_liquidity_risk = clamp01(1.0 - base_components.get("liquidity_health", 0.0))
    reversal_risk = clamp01(
        0.55 * normalized.get("sharp_short_term_reversal_risk", 0.0)
        + 0.45 * normalized.get("price_move_without_quality_improvement", 0.0)
    )
    weak_market_structure = clamp01(
        0.55 * (1.0 - normalized.get("market_structure_floor", 0.0))
        + 0.30 * (1.0 - normalized.get("market_relevance_proxy", 0.0))
        + 0.15 * (1.0 - normalized.get("update_freshness", 0.0))
    )
    fragility = clamp01(
        0.22 * crowding_level
        + 0.28 * concentration_risk
        + 0.24 * thin_liquidity_risk
        + 0.14 * reversal_risk
        + 0.12 * weak_market_structure
    )
    return {
        "crowding_level": crowding_level,
        "concentration_risk": concentration_risk,
        "thin_liquidity_risk": thin_liquidity_risk,
        "reversal_risk": reversal_risk,
        "weak_market_structure": weak_market_structure,
        "fragility": fragility,
    }
