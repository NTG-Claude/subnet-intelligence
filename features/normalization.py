import math

from scorer.normalizer import percentile_rank


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def absolute_piecewise(value: float | None, points: list[tuple[float, float]], *, inverse: bool = False) -> float:
    if value is None:
        return 0.0
    numeric = float(value)
    if not points:
        return 0.0
    if numeric <= points[0][0]:
        score = points[0][1]
    elif numeric >= points[-1][0]:
        score = points[-1][1]
    else:
        score = points[-1][1]
        for idx in range(1, len(points)):
            left_x, left_y = points[idx - 1]
            right_x, right_y = points[idx]
            if left_x <= numeric <= right_x:
                span = max(right_x - left_x, 1e-9)
                share = (numeric - left_x) / span
                score = left_y + share * (right_y - left_y)
                break
    score = clamp01(score)
    return clamp01(1.0 - score) if inverse else score


ABSOLUTE_SCORE_MAP: dict[str, tuple[list[tuple[float, float]], bool]] = {
    "reserve_depth": ([(0.0, 0.0), (500.0, 0.08), (2_500.0, 0.24), (10_000.0, 0.62), (75_000.0, 1.0)], False),
    "validator_participation": ([(0.0, 0.0), (0.15, 0.25), (0.35, 0.55), (0.60, 0.82), (0.90, 1.0)], False),
    "participation_breadth": ([(0.0, 0.0), (0.10, 0.18), (0.20, 0.42), (0.35, 0.70), (0.55, 1.0)], False),
    "liquidity_thinness": ([(0.0, 1.0), (0.01, 0.92), (0.03, 0.75), (0.08, 0.38), (0.20, 0.0)], False),
    "concentration": ([(0.0, 1.0), (0.20, 0.88), (0.35, 0.68), (0.55, 0.35), (0.80, 0.0)], False),
    "update_freshness": ([(0.0, 0.0), (0.20, 0.25), (0.45, 0.55), (0.70, 0.82), (0.95, 1.0)], False),
    "history_depth_score": ([(0.0, 0.0), (0.20, 0.20), (0.45, 0.50), (0.70, 0.78), (0.95, 1.0)], False),
}

BOUNDED_KEYS = {
    "active_ratio",
    "participation_breadth",
    "validator_participation",
    "incentive_distribution_quality",
    "update_freshness",
    "validator_weight_entropy",
    "cross_validator_disagreement",
    "meaningful_discrimination",
    "bond_responsiveness",
    "incentive_concentration",
    "validator_dominance",
    "liquidity_thinness",
    "flow_to_price_elasticity",
    "price_move_without_quality_improvement",
    "emission_spike_without_participation_improvement",
    "reserve_sensitivity",
    "crowding_proxy",
    "sharp_short_term_reversal_risk",
    "performance_driven_by_few_actors",
    "data_coverage",
    "validator_signal_coverage",
    "market_signal_coverage",
    "history_signal_coverage",
    "external_evidence_coverage",
    "consensus_signal_gap",
    "history_depth_score",
    "proxy_reliance_penalty",
    "low_manipulation_signal_share",
    "confidence_market_relevance",
    "market_relevance_proxy",
    "confidence_market_structure_floor",
    "market_structure_floor",
    "confidence_market_integrity",
    "confidence_thesis_coherence",
    "signal_fabrication_risk",
    "low_evidence_high_conviction",
    "repo_recency",
    "external_source_legitimacy",
    "external_dev_recency",
    "external_dev_continuity",
    "external_dev_breadth",
    "market_data_reliability",
    "validator_data_reliability",
    "history_data_reliability",
    "external_data_reliability",
}

POSITIVE_ONLY_KEYS = {
    "quality_acceleration",
    "liquidity_improvement_rate",
    "validator_diversity_trend",
    "expected_price_response_gap",
    "expected_reserve_response_gap",
    "cohort_implied_fair_value_gap",
    "underreaction_score",
    "price_response_lag_to_quality_shift",
    "emission_to_sticky_usage_conversion",
    "post_incentive_retention",
    "reserve_growth_without_price",
    "participation_without_crowding",
    "quality_change",
    "reserve_change",
}

NEUTRAL_WHEN_MISSING = {
    "validator_weight_entropy",
    "cross_validator_disagreement",
    "meaningful_discrimination",
    "bond_responsiveness",
}


def normalize_metric_value(key: str, value: float | None, population: list[float | None]) -> float:
    if key in ABSOLUTE_SCORE_MAP:
        points, inverse = ABSOLUTE_SCORE_MAP[key]
        absolute_score = absolute_piecewise(value, points, inverse=inverse)
        relative_score = percentile_rank(value, population)
        return clamp01(0.6 * absolute_score + 0.4 * relative_score)
    if key == "concentration":
        absolute_score = absolute_piecewise(value, ABSOLUTE_SCORE_MAP["concentration"][0])
        relative_score = 1.0 - percentile_rank(value, population)
        return clamp01(0.6 * absolute_score + 0.4 * relative_score)
    if key in BOUNDED_KEYS:
        if value is None and key in NEUTRAL_WHEN_MISSING:
            return 0.5
        return clamp01(value or 0.0)
    if key in POSITIVE_ONLY_KEYS:
        if value is None or value <= 0:
            return 0.0
        positive_population = [candidate for candidate in population if candidate is not None and candidate > 0]
        if not positive_population:
            return 0.0
        return percentile_rank(value, positive_population)
    if value is None:
        return 0.0
    if abs(value) <= 1e-9:
        return 0.0
    return percentile_rank(value, population)


def log_scaled(value: float | None, scale: float) -> float:
    if value is None or value <= 0:
        return 0.0
    return clamp01(math.log1p(value) / math.log1p(scale))
