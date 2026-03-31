import math
from collections import defaultdict
from statistics import fmean
from typing import Iterable

from collectors.models import HistoricalFeaturePoint, RawSubnetSnapshot
from features.types import AxisScores, FeatureBundle, FeatureMetric, PrimarySignals
from scorer.normalizer import percentile_rank


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def gini(values: Iterable[float]) -> float:
    clean = sorted(float(v) for v in values if v >= 0)
    if not clean:
        return 1.0
    total = sum(clean)
    if total <= 0:
        return 1.0
    n = len(clean)
    weighted = sum((idx + 1) * value for idx, value in enumerate(clean))
    return max(0.0, min(1.0, (2 * weighted) / (n * total) - (n + 1) / n))


def herfindahl(values: Iterable[float]) -> float:
    clean = [float(v) for v in values if v > 0]
    total = sum(clean)
    if total <= 0:
        return 1.0
    shares = [v / total for v in clean]
    return clamp01(sum(s * s for s in shares))


def normalized_entropy(values: Iterable[float]) -> float:
    clean = [float(v) for v in values if v > 0]
    if len(clean) <= 1:
        return 0.0
    total = sum(clean)
    shares = [v / total for v in clean]
    entropy = -sum(s * math.log(s) for s in shares if s > 0)
    return clamp01(entropy / math.log(len(shares)))


def mean_pairwise_l1(vectors: list[list[float]]) -> float:
    if len(vectors) <= 1:
        return 0.0
    distances: list[float] = []
    for idx, left in enumerate(vectors):
        for right in vectors[idx + 1:]:
            size = max(len(left), len(right))
            if size == 0:
                continue
            total = 0.0
            for pos in range(size):
                lval = left[pos] if pos < len(left) else 0.0
                rval = right[pos] if pos < len(right) else 0.0
                total += abs(lval - rval)
            distances.append(total / 2.0)
    return clamp01(fmean(distances)) if distances else 0.0


def simulate_tao_buy_slippage(tao_reserve: float, alpha_reserve: float, tao_in: float) -> float | None:
    if tao_reserve <= 0 or alpha_reserve <= 0 or tao_in <= 0:
        return None
    k = tao_reserve * alpha_reserve
    new_tao = tao_reserve + tao_in
    new_alpha = k / new_tao
    alpha_out = alpha_reserve - new_alpha
    if alpha_out <= 0:
        return 1.0
    spot_price = tao_reserve / alpha_reserve
    effective_price = tao_in / alpha_out
    return clamp01((effective_price - spot_price) / max(spot_price, 1e-9))


def _freshness(snapshot: RawSubnetSnapshot, lookback_blocks: int) -> float:
    if not snapshot.last_update_blocks:
        return 0.0
    recent = sum(1 for block in snapshot.last_update_blocks if block >= snapshot.current_block - lookback_blocks)
    denom = snapshot.yuma_neurons or snapshot.n_total or 1
    return clamp01(recent / denom)


def _history_values(history: list[HistoricalFeaturePoint], attr: str) -> list[float]:
    vals = [getattr(point, attr) for point in history]
    return [float(v) for v in vals if v is not None]


def _quality_history_series(history: list[HistoricalFeaturePoint]) -> list[float]:
    series: list[float] = []
    for point in history:
        if point.fundamental_quality is not None:
            series.append(float(point.fundamental_quality))
            continue
        candidates = [
            value
            for value in (
                point.intrinsic_quality,
                point.economic_sustainability,
            )
            if value is not None
        ]
        if candidates:
            series.append(float(fmean(candidates)))
    return series


def _current_quality_state(
    active_ratio: float,
    participation_breadth: float,
    validator_participation: float,
    incentive_distribution_quality: float,
) -> float:
    return clamp01(
        fmean(
            [
                active_ratio,
                participation_breadth,
                validator_participation,
                incentive_distribution_quality,
            ]
        )
    )


def _persistence(history: list[float]) -> float | None:
    if len(history) < 3:
        return None
    diffs = [abs(history[idx] - history[idx - 1]) for idx in range(1, len(history))]
    return clamp01(1.0 - min(1.0, fmean(diffs)))


def _acceleration(history: list[float]) -> float | None:
    if len(history) < 3:
        return None
    first = history[-2] - history[-3]
    second = history[-1] - history[-2]
    return second - first


def _change_vs_history(current: float, history: list[float]) -> float | None:
    if not history:
        return None
    anchor = history[-1]
    if abs(anchor) <= 1e-9:
        return None
    return (current - anchor) / abs(anchor)


def _trend_slope(history: list[float], periods: int = 4) -> float | None:
    if len(history) < 2:
        return None
    sample = history[-periods:]
    if len(sample) < 2:
        return None
    return (sample[-1] - sample[0]) / max(len(sample) - 1, 1)


def _history_anchor(history: list[float], fallback: float = 0.0) -> float:
    if not history:
        return fallback
    return history[-1]


def _coverage_ratio(values: dict[str, float | None], keys: list[str]) -> float:
    available = sum(1 for key in keys if values.get(key) is not None)
    return safe_ratio(available, len(keys))


def _market_relevance_proxy(
    reserve_depth: float,
    active_ratio: float,
    participation_breadth: float,
    validator_participation: float,
) -> float:
    reserve_score = clamp01(math.log1p(max(reserve_depth, 0.0)) / math.log(200_000))
    return clamp01(
        fmean(
            [
                reserve_score,
                active_ratio,
                participation_breadth,
                validator_participation,
            ]
        )
    )


def _market_structure_floor(
    reserve_depth: float,
    liquidity_thinness: float | None,
    active_ratio: float,
    participation_breadth: float,
    validator_participation: float,
) -> float:
    reserve_score = clamp01(math.log1p(max(reserve_depth, 0.0)) / math.log(50_000))
    liquidity_score = clamp01(1.0 - min(1.0, liquidity_thinness or 0.0))
    return clamp01(
        fmean(
            [
                reserve_score,
                liquidity_score,
                active_ratio,
                participation_breadth,
                validator_participation,
            ]
        )
    )


def _cohort_key(bundle: FeatureBundle) -> str:
    reserve_depth = bundle.raw.get("reserve_depth") or 0.0
    active_ratio = bundle.raw.get("active_ratio") or 0.0
    if reserve_depth >= 75_000:
        size = "deep"
    elif reserve_depth >= 10_000:
        size = "mid"
    else:
        size = "thin"
    if active_ratio >= 0.45:
        maturity = "mature"
    elif active_ratio >= 0.15:
        maturity = "forming"
    else:
        maturity = "nascent"
    return f"{size}:{maturity}"


def compute_raw_features(snapshot: RawSubnetSnapshot) -> FeatureBundle:
    yuma_neurons = snapshot.yuma_neurons or snapshot.n_total or 1
    active_ratio = safe_ratio(snapshot.active_neurons_7d, yuma_neurons)
    participation_breadth = safe_ratio(snapshot.unique_coldkeys, max(snapshot.n_total, 1))
    validator_participation = safe_ratio(snapshot.n_validators, yuma_neurons)
    incentive_distribution_quality = 1.0 - gini(snapshot.incentive_scores)
    incentive_concentration = herfindahl(snapshot.incentive_scores)
    validator_dominance = max(
        (max(snapshot.validator_stakes) / sum(snapshot.validator_stakes))
        if sum(snapshot.validator_stakes) > 0 and snapshot.validator_stakes else 1.0,
        snapshot.top3_stake_fraction,
    )
    validator_weight_entropy = (
        fmean(normalized_entropy(row) for row in snapshot.validator_weight_matrix)
        if snapshot.validator_weight_matrix else None
    )
    cross_validator_disagreement = (
        mean_pairwise_l1(snapshot.validator_weight_matrix)
        if snapshot.validator_weight_matrix else None
    )
    meaningful_discrimination = (
        fmean(1.0 - normalized_entropy(row) for row in snapshot.validator_weight_matrix)
        if snapshot.validator_weight_matrix else None
    )
    bond_responsiveness = (
        fmean(1.0 - normalized_entropy(row) for row in snapshot.validator_bond_matrix)
        if snapshot.validator_bond_matrix else None
    )

    slippage_1 = simulate_tao_buy_slippage(snapshot.tao_in_pool, snapshot.alpha_in_pool, 1.0)
    slippage_10 = simulate_tao_buy_slippage(snapshot.tao_in_pool, snapshot.alpha_in_pool, 10.0)
    slippage_50 = simulate_tao_buy_slippage(snapshot.tao_in_pool, snapshot.alpha_in_pool, 50.0)
    avg_slippage = (
        fmean(v for v in [slippage_1, slippage_10, slippage_50] if v is not None)
        if any(v is not None for v in [slippage_1, slippage_10, slippage_50]) else None
    )

    history = snapshot.history or []
    price_history = _history_values(history, "alpha_price_tao")
    quality_history = _quality_history_series(history)
    active_history = _history_values(history, "active_ratio")
    emission_history = _history_values(history, "emission_per_block_tao")
    flow_history = _history_values(history, "tao_in_pool")
    concentration_history = _history_values(history, "concentration_proxy")
    liquidity_history = _history_values(history, "liquidity_thinness")

    price_change = _change_vs_history(snapshot.alpha_price_tao, price_history)
    active_change = _change_vs_history(active_ratio, active_history)
    quality_change = _change_vs_history(
        _current_quality_state(
            active_ratio,
            participation_breadth,
            validator_participation,
            incentive_distribution_quality,
        ),
        quality_history,
    )
    emission_change = _change_vs_history(snapshot.emission_per_block_tao, emission_history)
    reserve_change = _change_vs_history(snapshot.tao_in_pool, flow_history)
    concentration_now = max(validator_dominance, incentive_concentration)
    concentration_change = _change_vs_history(concentration_now, concentration_history)
    liquidity_change = _change_vs_history(avg_slippage or 0.0, liquidity_history) if avg_slippage is not None else None

    quality_acceleration = _acceleration(quality_history)
    liquidity_improvement_rate = None
    if reserve_change is not None or liquidity_change is not None:
        liquidity_improvement_rate = (reserve_change or 0.0) - max(liquidity_change or 0.0, 0.0)
    validator_diversity_trend = None
    if concentration_change is not None:
        validator_diversity_trend = -concentration_change
    price_response_lag_to_quality_shift = max(0.0, (quality_change or 0.0) - max(price_change or 0.0, 0.0))
    emission_to_sticky_usage_conversion = max(0.0, (active_change or quality_change or 0.0) - max(emission_change or 0.0, 0.0))
    post_incentive_retention = max(
        0.0,
        (active_change or 0.0) - max(emission_change or 0.0, 0.0) + 0.5 * (quality_acceleration or 0.0),
    )
    reserve_growth_without_price = max(0.0, (reserve_change or 0.0) - max(price_change or 0.0, 0.0))
    participation_without_crowding = max(
        0.0,
        (active_change or 0.0) + max(validator_diversity_trend or 0.0, 0.0) - max(concentration_change or 0.0, 0.0),
    )
    reversal_risk = max(0.0, (price_change or 0.0) - max(quality_change or 0.0, 0.0))
    crowding_proxy = fmean([concentration_now, clamp01(avg_slippage or 0.0), clamp01(max(price_change or 0.0, 0.0))])
    market_relevance = _market_relevance_proxy(
        snapshot.tao_in_pool,
        active_ratio,
        participation_breadth,
        validator_participation,
    )
    market_structure_floor = _market_structure_floor(
        snapshot.tao_in_pool,
        avg_slippage,
        active_ratio,
        participation_breadth,
        validator_participation,
    )
    raw = {
        "active_ratio": active_ratio,
        "participation_breadth": participation_breadth,
        "validator_participation": validator_participation,
        "incentive_distribution_quality": incentive_distribution_quality,
        "update_freshness": _freshness(snapshot, lookback_blocks=7200),
        "validator_weight_entropy": validator_weight_entropy,
        "cross_validator_disagreement": cross_validator_disagreement,
        "meaningful_discrimination": meaningful_discrimination,
        "bond_responsiveness": bond_responsiveness,
        "incentive_concentration": incentive_concentration,
        "validator_dominance": validator_dominance,
        "reserve_depth": snapshot.tao_in_pool,
        "alpha_reserve": snapshot.alpha_in_pool,
        "tao_reserve": snapshot.tao_in_pool,
        "slippage_1_tao": slippage_1,
        "slippage_10_tao": slippage_10,
        "slippage_50_tao": slippage_50,
        "liquidity_thinness": avg_slippage,
        "emission_efficiency": safe_ratio(snapshot.total_stake_tao, max(snapshot.emission_per_block_tao, 1e-9)),
        "emission_concentration": incentive_concentration,
        "emission_persistence": _persistence(emission_history),
        "flow_stability": _persistence(flow_history),
        "flow_to_price_elasticity": safe_ratio(abs(price_change or 0.0), abs(reserve_change or 0.0) + 0.01),
        "price_move_without_quality_improvement": max(0.0, (price_change or 0.0) - max(quality_change or 0.0, 0.0)),
        "emission_spike_without_participation_improvement": max(0.0, (emission_change or 0.0) - max(quality_change or 0.0, 0.0)),
        "reserve_sensitivity": avg_slippage,
        "crowding_proxy": crowding_proxy,
        "sharp_short_term_reversal_risk": reversal_risk,
        "performance_driven_by_few_actors": concentration_now,
        "market_relevance_proxy": market_relevance,
        "confidence_market_relevance": market_relevance,
        "market_structure_floor": market_structure_floor,
        "confidence_market_structure_floor": market_structure_floor,
        "registration_openness": 1.0 if snapshot.registration_allowed else 0.0,
        "pow_registration_enabled": 1.0 if snapshot.difficulty > 0 else 0.0,
        "burn_registration_enabled": 1.0 if snapshot.min_burn > 0 or snapshot.max_burn > 0 else 0.0,
        "immunity_period": float(snapshot.immunity_period),
        "dereg_risk_proxy": clamp01(
            0.45 * max(0.0, 0.35 - active_ratio)
            + 0.25 * max(0.0, 0.20 - participation_breadth)
            + 0.20 * concentration_now
            + 0.10 * (1.0 if snapshot.registration_allowed else 0.0)
        ),
        "repo_commits_30d": float(snapshot.github.commits_30d) if snapshot.github else None,
        "repo_contributors_30d": float(snapshot.github.contributors_30d) if snapshot.github else None,
        "repo_recency": None if not snapshot.github or not snapshot.github.last_push else 1.0,
        "quality_acceleration": quality_acceleration,
        "liquidity_improvement_rate": liquidity_improvement_rate,
        "concentration_delta": concentration_change,
        "validator_diversity_trend": validator_diversity_trend,
        "price_response_lag_to_quality_shift": price_response_lag_to_quality_shift,
        "emission_to_sticky_usage_conversion": emission_to_sticky_usage_conversion,
        "post_incentive_retention": post_incentive_retention,
        "reserve_growth_without_price": reserve_growth_without_price,
        "participation_without_crowding": participation_without_crowding,
        "data_coverage": _coverage_ratio(
            {
                "validator_weight_entropy": validator_weight_entropy,
                "cross_validator_disagreement": cross_validator_disagreement,
                "meaningful_discrimination": meaningful_discrimination,
                "bond_responsiveness": bond_responsiveness,
                "slippage_10_tao": slippage_10,
                "slippage_50_tao": slippage_50,
                "emission_persistence": _persistence(emission_history),
                "flow_stability": _persistence(flow_history),
                "quality_acceleration": quality_acceleration,
                "liquidity_improvement_rate": liquidity_improvement_rate,
                "concentration_delta": concentration_change,
            },
            [
                "validator_weight_entropy",
                "cross_validator_disagreement",
                "meaningful_discrimination",
                "bond_responsiveness",
                "slippage_10_tao",
                "slippage_50_tao",
                "emission_persistence",
                "flow_stability",
                "quality_acceleration",
                "liquidity_improvement_rate",
                "concentration_delta",
            ],
        ),
        "history_depth_score": clamp01(len(history) / 6.0),
        "proxy_reliance_penalty": clamp01(
            0.45 * (1.0 - _freshness(snapshot, lookback_blocks=7200))
            + 0.35 * (1.0 - clamp01(len(history) / 6.0))
            + 0.20 * (1.0 if snapshot.github else 0.0)
        ),
        "low_manipulation_signal_share": clamp01(
            0.55 * _freshness(snapshot, lookback_blocks=7200)
            + 0.25 * (1.0 - concentration_now)
            + 0.20 * clamp01(1.0 - (0.5 if snapshot.github else 0.0))
        ),
        "quality_history_anchor": _history_anchor(quality_history),
        "price_history_anchor": _history_anchor(price_history),
    }
    return FeatureBundle(raw=raw)


METRIC_MAP = {
    "active_ratio": ("direct_onchain", "fundamental_quality", 0.12, False),
    "participation_breadth": ("direct_onchain", "fundamental_quality", 0.10, False),
    "validator_participation": ("direct_onchain", "fundamental_quality", 0.08, False),
    "incentive_distribution_quality": ("derived_onchain", "fundamental_quality", 0.10, False),
    "market_relevance_proxy": ("derived_onchain", "fundamental_quality", 0.06, False),
    "market_structure_floor": ("derived_onchain", "fundamental_quality", 0.10, False),
    "update_freshness": ("direct_onchain", "signal_confidence", 0.18, False),
    "validator_weight_entropy": ("derived_onchain", "fundamental_quality", 0.05, False),
    "cross_validator_disagreement": ("derived_onchain", "fundamental_quality", 0.10, False),
    "meaningful_discrimination": ("derived_onchain", "fundamental_quality", 0.10, False),
    "bond_responsiveness": ("derived_onchain", "fundamental_quality", 0.08, False),
    "incentive_concentration": ("derived_onchain", "fragility_risk", 0.10, False),
    "validator_dominance": ("derived_onchain", "fragility_risk", 0.12, False),
    "reserve_depth": ("direct_onchain", "fundamental_quality", 0.08, False),
    "slippage_10_tao": ("simulated", "fragility_risk", 0.08, False),
    "slippage_50_tao": ("simulated", "fragility_risk", 0.10, False),
    "liquidity_thinness": ("simulated", "fragility_risk", 0.12, False),
    "emission_efficiency": ("derived_onchain", "fundamental_quality", 0.07, False),
    "emission_concentration": ("derived_onchain", "fragility_risk", 0.05, False),
    "emission_persistence": ("needs_history", "fundamental_quality", 0.05, False),
    "flow_stability": ("needs_history", "fundamental_quality", 0.05, False),
    "flow_to_price_elasticity": ("needs_history", "fragility_risk", 0.07, False),
    "price_move_without_quality_improvement": ("needs_history", "fragility_risk", 0.07, False),
    "emission_spike_without_participation_improvement": ("needs_history", "fragility_risk", 0.07, False),
    "reserve_sensitivity": ("simulated", "fragility_risk", 0.06, False),
    "crowding_proxy": ("derived_onchain", "fragility_risk", 0.07, False),
    "sharp_short_term_reversal_risk": ("needs_history", "fragility_risk", 0.05, False),
    "performance_driven_by_few_actors": ("derived_onchain", "fragility_risk", 0.06, False),
    "quality_acceleration": ("needs_history", "mispricing_signal", 0.12, False),
    "liquidity_improvement_rate": ("needs_history", "mispricing_signal", 0.10, False),
    "concentration_delta": ("needs_history", "mispricing_signal", 0.08, True),
    "validator_diversity_trend": ("needs_history", "mispricing_signal", 0.07, False),
    "price_response_lag_to_quality_shift": ("needs_history", "mispricing_signal", 0.16, False),
    "emission_to_sticky_usage_conversion": ("needs_history", "mispricing_signal", 0.12, False),
    "post_incentive_retention": ("needs_history", "mispricing_signal", 0.10, False),
    "reserve_growth_without_price": ("needs_history", "mispricing_signal", 0.10, False),
    "participation_without_crowding": ("needs_history", "mispricing_signal", 0.09, False),
    "data_coverage": ("derived_onchain", "signal_confidence", 0.20, False),
    "history_depth_score": ("needs_history", "signal_confidence", 0.18, False),
    "proxy_reliance_penalty": ("derived_onchain", "signal_confidence", 0.20, True),
    "low_manipulation_signal_share": ("derived_onchain", "signal_confidence", 0.16, False),
    "confidence_market_relevance": ("derived_onchain", "signal_confidence", 0.06, False),
    "confidence_market_structure_floor": ("derived_onchain", "signal_confidence", 0.10, False),
    "repo_commits_30d": ("external_proxy", "signal_confidence", 0.04, False),
    "repo_contributors_30d": ("external_proxy", "signal_confidence", 0.04, False),
    "repo_recency": ("external_proxy", "signal_confidence", 0.02, False),
}


def _normalize_metric_value(key: str, value: float | None, population: list[float | None]) -> float:
    bounded = {
        "participation_breadth",
        "incentive_distribution_quality",
        "validator_weight_entropy",
        "cross_validator_disagreement",
        "meaningful_discrimination",
        "bond_responsiveness",
        "update_freshness",
        "data_coverage",
        "history_depth_score",
        "proxy_reliance_penalty",
        "low_manipulation_signal_share",
        "repo_recency",
    }
    if key in bounded:
        return 0.5 if value is None and key in {
            "validator_weight_entropy",
            "cross_validator_disagreement",
            "meaningful_discrimination",
            "bond_responsiveness",
        } else clamp01(value or 0.0)
    return percentile_rank(value, population)


def _build_cohort_edges(raw_bundles: list[FeatureBundle]) -> None:
    by_cohort: dict[str, list[FeatureBundle]] = defaultdict(list)
    for bundle in raw_bundles:
        by_cohort[_cohort_key(bundle)].append(bundle)

    for group in by_cohort.values():
        quality_population = [b.raw.get("active_ratio") for b in group]
        reserve_population = [b.raw.get("reserve_depth") for b in group]
        change_population = [b.raw.get("price_response_lag_to_quality_shift") for b in group]
        relevance_population = [b.raw.get("market_relevance_proxy") for b in group]
        for bundle in group:
            bundle.raw["cohort_quality_edge"] = percentile_rank(bundle.raw.get("active_ratio"), quality_population)
            bundle.raw["cohort_liquidity_edge"] = percentile_rank(bundle.raw.get("reserve_depth"), reserve_population)
            bundle.raw["cohort_mispricing_edge"] = percentile_rank(bundle.raw.get("price_response_lag_to_quality_shift"), change_population)
            bundle.raw["cohort_relevance_edge"] = percentile_rank(bundle.raw.get("market_relevance_proxy"), relevance_population)


def _inject_cohort_metrics(bundle: FeatureBundle) -> None:
    for name, category, output, weight in [
        ("cohort_quality_edge", "cohort_relative", "fundamental_quality", 0.02),
        ("cohort_liquidity_edge", "cohort_relative", "fundamental_quality", 0.02),
        ("cohort_relevance_edge", "cohort_relative", "fundamental_quality", 0.03),
        ("cohort_mispricing_edge", "cohort_relative", "mispricing_signal", 0.06),
        ("cohort_relevance_edge", "cohort_relative", "signal_confidence", 0.04),
    ]:
        value = bundle.raw.get(name)
        bundle.metrics[name] = FeatureMetric(
            name=name,
            value=value,
            normalized=clamp01(value or 0.0),
            category=category,
            axis=output,
            weight=weight,
            higher_is_better=True,
        )


def _weighted_output(bundle: FeatureBundle, output: str) -> float:
    selected = [metric for metric in bundle.metrics.values() if metric.axis == output and metric.weight > 0]
    if not selected:
        return 0.0
    total_weight = sum(metric.weight for metric in selected)
    total = 0.0
    for metric in selected:
        value = metric.normalized if metric.higher_is_better else (1.0 - metric.normalized)
        total += value * metric.weight
    return total / total_weight


def _legacy_axes_from_primary(primary: PrimarySignals, bundle: FeatureBundle) -> AxisScores:
    intrinsic = clamp01(0.82 * primary.fundamental_quality + 0.18 * bundle.raw.get("cohort_quality_edge", 0.0))
    economic = clamp01(
        0.45 * primary.fundamental_quality
        + 0.35 * (1.0 - primary.fragility_risk)
        + 0.20 * clamp01(bundle.raw.get("flow_stability") or 0.0)
    )
    reflexivity = clamp01(
        0.55 * primary.fragility_risk
        + 0.30 * clamp01(bundle.raw.get("crowding_proxy") or 0.0)
        + 0.15 * max(0.0, 1.0 - primary.mispricing_signal)
    )
    stress_robustness = clamp01(1.0 - primary.fragility_risk)
    opportunity_gap = max(-1.0, min(1.0, (primary.mispricing_signal - 0.5) * 2.0))
    return AxisScores(
        intrinsic_quality=intrinsic,
        economic_sustainability=economic,
        reflexivity=reflexivity,
        stress_robustness=stress_robustness,
        opportunity_gap=opportunity_gap,
    )


def normalize_features(raw_bundles: list[FeatureBundle]) -> list[FeatureBundle]:
    _build_cohort_edges(raw_bundles)
    all_values = {key: [bundle.raw.get(key) for bundle in raw_bundles] for key in METRIC_MAP}

    for bundle in raw_bundles:
        metrics: dict[str, FeatureMetric] = {}
        for key, (category, output, weight, inverse) in METRIC_MAP.items():
            value = bundle.raw.get(key)
            metrics[key] = FeatureMetric(
                name=key,
                value=value,
                normalized=_normalize_metric_value(key, value, all_values[key]),
                category=category,
                axis=output,
                weight=weight,
                higher_is_better=not inverse,
            )
        bundle.metrics = metrics
        _inject_cohort_metrics(bundle)
        primary = PrimarySignals(
            fundamental_quality=clamp01(_weighted_output(bundle, "fundamental_quality")),
            mispricing_signal=clamp01(_weighted_output(bundle, "mispricing_signal")),
            fragility_risk=clamp01(_weighted_output(bundle, "fragility_risk")),
            signal_confidence=clamp01(_weighted_output(bundle, "signal_confidence")),
        )
        bundle.primary_signals = primary
        bundle.axes = _legacy_axes_from_primary(primary, bundle)
    return raw_bundles
