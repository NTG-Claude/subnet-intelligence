from features.normalization import clamp01


def _stabilize_underreaction(value: float) -> float:
    if value >= 0.5:
        return value
    # Keep weak opportunity from becoming an outsized penalty while preserving
    # clear separation between low and high underreaction states.
    return clamp01(0.225 + 0.55 * value)


def build_opportunity_components(raw: dict[str, float | None], normalized: dict[str, float]) -> dict[str, float]:
    quality_momentum = clamp01(
        0.55 * normalized.get("quality_change", 0.0)
        + 0.45 * normalized.get("quality_acceleration", 0.0)
    )
    reserve_momentum = clamp01(
        0.60 * normalized.get("reserve_change", 0.0)
        + 0.40 * normalized.get("reserve_growth_without_price", 0.0)
    )
    price_lag = clamp01(
        0.65 * normalized.get("price_response_lag_to_quality_shift", 0.0)
        + 0.35 * normalized.get("expected_price_response_gap", 0.0)
    )
    participation_level_support = clamp01(
        0.45 * normalized.get("active_ratio", 0.0)
        + 0.35 * normalized.get("participation_breadth", 0.0)
        + 0.20 * normalized.get("validator_participation", 0.0)
    )
    uncrowded_participation = clamp01(
        0.45 * normalized.get("participation_without_crowding", 0.0)
        + 0.20 * normalized.get("participation_breadth", 0.0)
        + 0.15 * (1.0 - normalized.get("crowding_proxy", 0.0))
        + 0.20 * participation_level_support
    )
    fair_value_gap_light = clamp01(
        0.55 * normalized.get("cohort_implied_fair_value_gap", 0.0)
        + 0.45 * normalized.get("underreaction_score", 0.0)
    )
    raw_opportunity_underreaction = clamp01(
        0.24 * quality_momentum
        + 0.20 * reserve_momentum
        + 0.22 * price_lag
        + 0.16 * uncrowded_participation
        + 0.18 * fair_value_gap_light
    )
    opportunity_underreaction = _stabilize_underreaction(raw_opportunity_underreaction)
    return {
        "quality_momentum": quality_momentum,
        "reserve_momentum": reserve_momentum,
        "price_lag": price_lag,
        "uncrowded_participation": uncrowded_participation,
        "fair_value_gap_light": fair_value_gap_light,
        "raw_opportunity_underreaction": raw_opportunity_underreaction,
        "opportunity_underreaction": opportunity_underreaction,
    }
