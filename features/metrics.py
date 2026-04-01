import math
from collections import defaultdict
from datetime import datetime
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
    ages = [max(snapshot.current_block - block, 0) for block in snapshot.last_update_blocks if block is not None]
    if not ages:
        return 0.0
    recent_share = safe_ratio(sum(1 for age in ages if age <= lookback_blocks), len(ages))
    median_age = sorted(ages)[len(ages) // 2]
    age_decay = math.exp(-safe_ratio(median_age, max(lookback_blocks * 1.5, 1)))
    coverage = safe_ratio(
        len(ages),
        max(snapshot.yuma_neurons or snapshot.n_total or len(ages), 1),
    )
    return clamp01(0.55 * recent_share + 0.35 * age_decay + 0.10 * coverage)


def _parse_iso_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _history_depth_score(history: list[HistoricalFeaturePoint]) -> float:
    if not history:
        return 0.0
    expected_fields = [
        "alpha_price_tao",
        "tao_in_pool",
        "emission_per_block_tao",
        "active_ratio",
        "concentration_proxy",
        "liquidity_thinness",
        "fundamental_quality",
    ]
    field_presence = [
        safe_ratio(
            sum(1 for point in history if getattr(point, field) is not None),
            len(history),
        )
        for field in expected_fields
    ]
    avg_field_presence = fmean(field_presence) if field_presence else 0.0
    parsed_timestamps = [dt for dt in (_parse_iso_timestamp(point.timestamp) for point in history) if dt is not None]
    unique_days = len({dt.date() for dt in parsed_timestamps})
    point_depth = clamp01(len(history) / 18.0)
    time_depth = clamp01(unique_days / 14.0)
    return clamp01(
        0.40 * point_depth
        + 0.35 * avg_field_presence
        + 0.25 * time_depth
    )


def _history_values(history: list[HistoricalFeaturePoint], attr: str) -> list[float]:
    vals = [getattr(point, attr) for point in history]
    return [float(v) for v in vals if v is not None]


def _quality_history_series(history: list[HistoricalFeaturePoint]) -> list[float]:
    series: list[float] = []
    for point in history:
        direct_components = [
            value
            for value in (
                point.active_ratio,
                point.participation_breadth,
                point.validator_participation,
                point.incentive_distribution_quality,
                point.market_structure_floor,
            )
            if value is not None
        ]
        if len(direct_components) >= 3:
            series.append(clamp01(fmean(direct_components)))
            continue
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


def _latest_trend_change(history: list[float], periods: int = 4) -> float | None:
    slope = _trend_slope(history, periods=periods)
    if slope is None:
        return None
    anchor = history[-1] if history else 0.0
    scale = max(abs(anchor), 0.05)
    return slope / scale


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


def _signal_presence_ratio(values: list[float | None]) -> float:
    if not values:
        return 0.0
    available = sum(1 for value in values if value is not None)
    return clamp01(available / len(values))


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


def _confidence_market_integrity(
    market_structure_floor: float,
    dereg_risk_proxy: float,
    crowding_proxy: float,
    liquidity_thinness: float | None,
) -> float:
    return clamp01(
        0.40 * market_structure_floor
        + 0.25 * (1.0 - dereg_risk_proxy)
        + 0.20 * (1.0 - crowding_proxy)
        + 0.15 * (1.0 - clamp01(liquidity_thinness or 0.0))
    )


def _confidence_thesis_coherence(
    reversal_risk: float,
    price_move_without_quality_improvement: float,
    emission_spike_without_participation_improvement: float,
    flow_to_price_elasticity: float,
) -> float:
    contradiction = clamp01(
        0.35 * reversal_risk
        + 0.30 * price_move_without_quality_improvement
        + 0.20 * emission_spike_without_participation_improvement
        + 0.15 * clamp01(max(0.0, flow_to_price_elasticity - 1.0))
    )
    return clamp01(1.0 - contradiction)


def _expected_price_response(
    quality_change: float | None,
    reserve_change: float | None,
    active_change: float | None,
    validator_diversity_trend: float | None,
) -> float:
    return max(
        0.0,
        0.45 * max(quality_change or 0.0, 0.0)
        + 0.25 * max(reserve_change or 0.0, 0.0)
        + 0.20 * max(active_change or 0.0, 0.0)
        + 0.10 * max(validator_diversity_trend or 0.0, 0.0),
    )


def _expected_reserve_response(
    quality_change: float | None,
    active_change: float | None,
    emission_to_sticky_usage_conversion: float | None,
    post_incentive_retention: float | None,
) -> float:
    return max(
        0.0,
        0.40 * max(quality_change or 0.0, 0.0)
        + 0.30 * max(active_change or 0.0, 0.0)
        + 0.20 * max(emission_to_sticky_usage_conversion or 0.0, 0.0)
        + 0.10 * max(post_incentive_retention or 0.0, 0.0),
    )


def _signal_fabrication_risk(
    proxy_reliance_penalty: float,
    data_coverage: float,
    consensus_signal_gap: float,
    confidence_thesis_coherence: float,
    overreaction_score: float,
    crowding_proxy: float,
    low_manipulation_signal_share: float,
    market_structure_floor: float,
    market_relevance: float,
) -> float:
    return clamp01(
        0.35 * proxy_reliance_penalty
        + 0.18 * (1.0 - data_coverage)
        + 0.14 * consensus_signal_gap
        + 0.16 * (1.0 - confidence_thesis_coherence)
        + 0.12 * overreaction_score
        + 0.08 * crowding_proxy
        - 0.12 * low_manipulation_signal_share
        - 0.10 * market_structure_floor
        - 0.08 * market_relevance
    )


def _mispricing_structural_drag(
    market_structure_floor: float,
    market_relevance: float,
    crowding_proxy: float,
    overreaction_score: float,
    signal_fabrication_risk: float,
    fragility_excess: float,
    yield_heat: float,
) -> float:
    return clamp01(
        0.26 * (1.0 - market_structure_floor)
        + 0.16 * (1.0 - market_relevance)
        + 0.14 * crowding_proxy
        + 0.14 * overreaction_score
        + 0.12 * signal_fabrication_risk
        + 0.10 * fragility_excess
        + 0.08 * yield_heat
    )


def _crowded_repricing_discount(
    market_relevance: float,
    market_structure_floor: float,
    crowding_proxy: float,
    underreaction_score: float,
    overreaction_score: float,
    fragility_excess: float,
) -> float:
    crowded_flag = clamp01(
        0.30 * market_relevance
        + 0.20 * market_structure_floor
        + 0.35 * crowding_proxy
        + 0.15 * underreaction_score
    )
    return clamp01(
        crowded_flag
        * (
            0.50 * crowding_proxy
            + 0.22 * underreaction_score
            + 0.18 * fragility_excess
            + 0.10 * overreaction_score
        )
    )


def _crowded_expectation_saturation(
    market_relevance: float,
    crowding_proxy: float,
    realized_price_level: float,
) -> float:
    return clamp01(
        0.45 * market_relevance
        + 0.35 * crowding_proxy
        + 0.20 * realized_price_level
    )


def _crowded_structure_penalty(
    market_relevance: float,
    market_structure_floor: float,
    crowding_proxy: float,
    concentration: float,
    staking_apy: float,
) -> float:
    yield_heat = clamp01(max(staking_apy - 70.0, 0.0) / 100.0)
    return clamp01(
        0.28 * market_relevance
        + 0.26 * crowding_proxy
        + 0.22 * concentration
        + 0.14 * yield_heat
        + 0.10 * max(market_structure_floor - 0.55, 0.0)
    )


def _cohort_key(bundle: FeatureBundle) -> str:
    reserve_depth = bundle.raw.get("reserve_depth") or 0.0
    active_ratio = bundle.raw.get("active_ratio") or 0.0
    emission_efficiency = bundle.raw.get("emission_efficiency") or 0.0
    participation_breadth = bundle.raw.get("participation_breadth") or 0.0
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
    emission_profile = "efficient" if emission_efficiency >= 5_000 else "subsidized"
    breadth = "broad" if participation_breadth >= 0.35 else "narrow"
    return f"{size}:{maturity}:{emission_profile}:{breadth}"


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
    breadth_history = _history_values(history, "participation_breadth")
    validator_history = _history_values(history, "validator_participation")
    structure_history = _history_values(history, "market_structure_floor")
    emission_history = _history_values(history, "emission_per_block_tao")
    flow_history = _history_values(history, "tao_in_pool")
    concentration_history = _history_values(history, "concentration_proxy")
    liquidity_history = _history_values(history, "liquidity_thinness")

    price_change = _change_vs_history(snapshot.alpha_price_tao, price_history)
    active_change = _change_vs_history(active_ratio, active_history)
    breadth_change = _change_vs_history(participation_breadth, breadth_history)
    validator_change = _change_vs_history(validator_participation, validator_history)
    structure_change = _change_vs_history(market_structure_floor := _market_structure_floor(
        snapshot.tao_in_pool,
        avg_slippage,
        active_ratio,
        participation_breadth,
        validator_participation,
    ), structure_history)
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

    quality_level_change = _latest_trend_change(quality_history)
    quality_acceleration = _acceleration(quality_history)
    if quality_acceleration is None:
        quality_acceleration = quality_level_change
    elif quality_level_change is not None:
        quality_acceleration = 0.6 * quality_acceleration + 0.4 * quality_level_change
    liquidity_improvement_rate = None
    if reserve_change is not None or liquidity_change is not None:
        liquidity_improvement_rate = (reserve_change or 0.0) - max(liquidity_change or 0.0, 0.0)
    validator_diversity_trend = None
    if concentration_change is not None:
        validator_diversity_trend = -concentration_change
    quality_shift = max(
        0.0,
        0.45 * max(quality_change or 0.0, 0.0)
        + 0.20 * max(breadth_change or 0.0, 0.0)
        + 0.15 * max(validator_change or 0.0, 0.0)
        + 0.20 * max(structure_change or 0.0, 0.0),
    )
    usage_stickiness_shift = max(
        0.0,
        0.40 * max(active_change or 0.0, 0.0)
        + 0.25 * max(breadth_change or 0.0, 0.0)
        + 0.20 * max(structure_change or 0.0, 0.0)
        + 0.15 * max(quality_acceleration or 0.0, 0.0),
    )
    price_response_lag_to_quality_shift = max(0.0, quality_shift - max(price_change or 0.0, 0.0))
    emission_to_sticky_usage_conversion = max(0.0, usage_stickiness_shift - max(emission_change or 0.0, 0.0))
    post_incentive_retention = max(
        0.0,
        0.55 * usage_stickiness_shift
        + 0.25 * max(quality_shift - max(emission_change or 0.0, 0.0), 0.0)
        + 0.20 * max(structure_change or 0.0, 0.0),
    )
    post_incentive_retention = max(
        0.0,
        post_incentive_retention
        - 0.50 * max(price_change or 0.0, 0.0)
        - 0.35 * max((emission_change or 0.0) - usage_stickiness_shift, 0.0),
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
    staking_apy_proxy = 0.0
    if snapshot.tao_in_pool and snapshot.tao_in_pool > 0:
        staking_apy_proxy = max(0.0, snapshot.emission_per_block_tao * 7200 * 365 / snapshot.tao_in_pool * 100)
    dereg_risk_proxy = clamp01(
        0.45 * max(0.0, 0.35 - active_ratio)
        + 0.25 * max(0.0, 0.20 - participation_breadth)
        + 0.20 * concentration_now
        + 0.10 * (1.0 if snapshot.registration_allowed else 0.0)
    )
    flow_to_price_elasticity = safe_ratio(abs(price_change or 0.0), abs(reserve_change or 0.0) + 0.01)
    confidence_market_integrity = _confidence_market_integrity(
        market_structure_floor,
        dereg_risk_proxy,
        crowding_proxy,
        avg_slippage,
    )
    confidence_thesis_coherence = _confidence_thesis_coherence(
        reversal_risk,
        max(0.0, (price_change or 0.0) - max(quality_change or 0.0, 0.0)),
        max(0.0, (emission_change or 0.0) - max(quality_change or 0.0, 0.0)),
        flow_to_price_elasticity,
    )
    validator_signal_coverage = _signal_presence_ratio(
        [
            validator_weight_entropy,
            cross_validator_disagreement,
            meaningful_discrimination,
            bond_responsiveness,
        ]
    )
    market_signal_coverage = _signal_presence_ratio(
        [
            slippage_1,
            slippage_10,
            slippage_50,
            avg_slippage,
            snapshot.alpha_price_tao,
            snapshot.tao_in_pool,
            snapshot.alpha_in_pool,
        ]
    )
    history_signal_coverage = _signal_presence_ratio(
        [
            _persistence(emission_history),
            _persistence(flow_history),
            quality_acceleration,
            liquidity_improvement_rate,
            concentration_change,
            validator_diversity_trend,
            price_response_lag_to_quality_shift,
            emission_to_sticky_usage_conversion,
            post_incentive_retention,
        ]
    )
    external_evidence_coverage = _signal_presence_ratio(
        [
            float(snapshot.github.commits_30d) if snapshot.github else None,
            float(snapshot.github.contributors_30d) if snapshot.github else None,
            1.0 if snapshot.github and snapshot.github.last_push else None,
        ]
    )
    data_coverage = clamp01(
        0.40 * market_signal_coverage
        + 0.35 * history_signal_coverage
        + 0.15 * external_evidence_coverage
        + 0.10 * validator_signal_coverage
    )
    consensus_signal_gap = clamp01(1.0 - validator_signal_coverage)
    expected_price_response = _expected_price_response(
        quality_change,
        reserve_change,
        active_change,
        validator_diversity_trend,
    )
    expected_reserve_response = _expected_reserve_response(
        quality_change,
        active_change,
        emission_to_sticky_usage_conversion,
        post_incentive_retention,
    )
    realized_price_response = max(price_change or 0.0, 0.0)
    realized_reserve_response = max(reserve_change or 0.0, 0.0)
    expected_price_response_gap = expected_price_response - realized_price_response
    expected_reserve_response_gap = expected_reserve_response - realized_reserve_response
    fair_value_anchor = clamp01(
        0.40 * market_relevance
        + 0.30 * market_structure_floor
        + 0.20 * confidence_market_integrity
        + 0.10 * clamp01(_history_anchor(quality_history))
    )
    realized_price_level = percentile_rank(snapshot.alpha_price_tao, price_history + [snapshot.alpha_price_tao])
    crowded_expectation_saturation = _crowded_expectation_saturation(
        market_relevance=market_relevance,
        crowding_proxy=crowding_proxy,
        realized_price_level=realized_price_level,
    )
    raw_cohort_implied_fair_value_gap = fair_value_anchor - realized_price_level
    cohort_implied_fair_value_gap = (
        max(raw_cohort_implied_fair_value_gap, 0.0) * (1.0 - 0.55 * crowded_expectation_saturation)
        - max(-raw_cohort_implied_fair_value_gap, 0.0)
    )
    raw_underreaction_score = clamp01(
        0.45 * max(expected_price_response_gap, 0.0)
        + 0.30 * max(expected_reserve_response_gap, 0.0)
        + 0.25 * max(cohort_implied_fair_value_gap, 0.0)
    )
    underreaction_score = clamp01(raw_underreaction_score * (1.0 - 0.45 * crowded_expectation_saturation))
    overreaction_score = clamp01(
        0.50 * max(realized_price_response - expected_price_response, 0.0)
        + 0.30 * max(realized_price_level - fair_value_anchor, 0.0)
        + 0.20 * reversal_risk
    )
    freshness = _freshness(snapshot, lookback_blocks=7200)
    history_depth_score = _history_depth_score(history)
    onchain_evidence_support = clamp01(
        0.40 * market_structure_floor
        + 0.30 * market_relevance
        + 0.20 * (1.0 - concentration_now)
        + 0.10 * active_ratio
    )
    proxy_reliance_penalty = clamp01(
        (
            0.30 * (1.0 - freshness)
            + 0.20 * (1.0 - history_depth_score)
            + 0.16 * (1.0 if snapshot.github else 0.0)
            + 0.12 * (1.0 - data_coverage)
            + 0.10 * crowding_proxy
            + 0.12 * consensus_signal_gap
        )
        * (1.0 - 0.45 * onchain_evidence_support)
    )
    low_manipulation_signal_share = clamp01(
        0.24 * freshness
        + 0.22 * (1.0 - concentration_now)
        + 0.22 * market_structure_floor
        + 0.20 * market_relevance
        + 0.08 * data_coverage
        + 0.06 * (1.0 - consensus_signal_gap)
    )
    signal_fabrication_risk = _signal_fabrication_risk(
        proxy_reliance_penalty,
        data_coverage,
        consensus_signal_gap,
        confidence_thesis_coherence,
        overreaction_score,
        crowding_proxy,
        low_manipulation_signal_share,
        market_structure_floor,
        market_relevance,
    )
    low_evidence_high_conviction = clamp01(
        0.55 * signal_fabrication_risk
        + 0.25 * max(underreaction_score - data_coverage, 0.0)
        + 0.20 * max(underreaction_score - confidence_thesis_coherence, 0.0)
    )
    raw = {
        "active_ratio": active_ratio,
        "participation_breadth": participation_breadth,
        "validator_participation": validator_participation,
        "incentive_distribution_quality": incentive_distribution_quality,
        "update_freshness": freshness,
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
        "flow_to_price_elasticity": flow_to_price_elasticity,
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
        "staking_apy_proxy": staking_apy_proxy,
        "registration_openness": 1.0 if snapshot.registration_allowed else 0.0,
        "pow_registration_enabled": 1.0 if snapshot.difficulty > 0 else 0.0,
        "burn_registration_enabled": 1.0 if snapshot.min_burn > 0 or snapshot.max_burn > 0 else 0.0,
        "immunity_period": float(snapshot.immunity_period),
        "dereg_risk_proxy": dereg_risk_proxy,
        "repo_commits_30d": float(snapshot.github.commits_30d) if snapshot.github else None,
        "repo_contributors_30d": float(snapshot.github.contributors_30d) if snapshot.github else None,
        "repo_recency": None if not snapshot.github or not snapshot.github.last_push else 1.0,
        "confidence_market_integrity": confidence_market_integrity,
        "confidence_thesis_coherence": confidence_thesis_coherence,
        "quality_acceleration": quality_acceleration,
        "liquidity_improvement_rate": liquidity_improvement_rate,
        "concentration_delta": concentration_change,
        "validator_diversity_trend": validator_diversity_trend,
        "price_response_lag_to_quality_shift": price_response_lag_to_quality_shift,
        "emission_to_sticky_usage_conversion": emission_to_sticky_usage_conversion,
        "post_incentive_retention": post_incentive_retention,
        "reserve_growth_without_price": reserve_growth_without_price,
        "participation_without_crowding": participation_without_crowding,
        "data_coverage": data_coverage,
        "validator_signal_coverage": validator_signal_coverage,
        "market_signal_coverage": market_signal_coverage,
        "history_signal_coverage": history_signal_coverage,
        "external_evidence_coverage": external_evidence_coverage,
        "consensus_signal_gap": consensus_signal_gap,
        "history_depth_score": history_depth_score,
        "onchain_evidence_support": onchain_evidence_support,
        "proxy_reliance_penalty": proxy_reliance_penalty,
        "low_manipulation_signal_share": low_manipulation_signal_share,
        "quality_history_anchor": _history_anchor(quality_history),
        "price_history_anchor": _history_anchor(price_history),
        "expected_price_response": expected_price_response,
        "realized_price_response": realized_price_response,
        "expected_price_response_gap": expected_price_response_gap,
        "expected_reserve_response": expected_reserve_response,
        "realized_reserve_response": realized_reserve_response,
        "expected_reserve_response_gap": expected_reserve_response_gap,
        "crowded_expectation_saturation": crowded_expectation_saturation,
        "raw_cohort_implied_fair_value_gap": raw_cohort_implied_fair_value_gap,
        "cohort_implied_fair_value_gap": cohort_implied_fair_value_gap,
        "raw_underreaction_score": raw_underreaction_score,
        "underreaction_score": underreaction_score,
        "overreaction_score": overreaction_score,
        "signal_fabrication_risk": signal_fabrication_risk,
        "low_evidence_high_conviction": low_evidence_high_conviction,
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
    "validator_weight_entropy": ("derived_onchain", "fundamental_quality", 0.0, False),
    "cross_validator_disagreement": ("derived_onchain", "fundamental_quality", 0.0, False),
    "meaningful_discrimination": ("derived_onchain", "fundamental_quality", 0.0, False),
    "bond_responsiveness": ("derived_onchain", "fundamental_quality", 0.0, False),
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
    "expected_price_response_gap": ("needs_history", "mispricing_signal", 0.13, False),
    "expected_reserve_response_gap": ("needs_history", "mispricing_signal", 0.10, False),
    "cohort_implied_fair_value_gap": ("cohort_relative", "mispricing_signal", 0.11, False),
    "underreaction_score": ("needs_history", "mispricing_signal", 0.14, False),
    "overreaction_score": ("needs_history", "mispricing_signal", 0.09, True),
    "price_response_lag_to_quality_shift": ("needs_history", "mispricing_signal", 0.16, False),
    "emission_to_sticky_usage_conversion": ("needs_history", "mispricing_signal", 0.12, False),
    "post_incentive_retention": ("needs_history", "mispricing_signal", 0.10, False),
    "reserve_growth_without_price": ("needs_history", "mispricing_signal", 0.10, False),
    "participation_without_crowding": ("needs_history", "mispricing_signal", 0.09, False),
    "data_coverage": ("derived_onchain", "signal_confidence", 0.20, False),
    "consensus_signal_gap": ("derived_onchain", "signal_confidence", 0.14, True),
    "history_depth_score": ("needs_history", "signal_confidence", 0.18, False),
    "proxy_reliance_penalty": ("derived_onchain", "signal_confidence", 0.20, True),
    "low_manipulation_signal_share": ("derived_onchain", "signal_confidence", 0.16, False),
    "confidence_market_relevance": ("derived_onchain", "signal_confidence", 0.06, False),
    "confidence_market_structure_floor": ("derived_onchain", "signal_confidence", 0.10, False),
    "confidence_market_integrity": ("derived_onchain", "signal_confidence", 0.16, False),
    "confidence_thesis_coherence": ("needs_history", "signal_confidence", 0.18, False),
    "signal_fabrication_risk": ("derived_onchain", "signal_confidence", 0.12, True),
    "low_evidence_high_conviction": ("derived_onchain", "signal_confidence", 0.08, True),
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
        "consensus_signal_gap",
        "history_depth_score",
        "proxy_reliance_penalty",
        "low_manipulation_signal_share",
        "confidence_market_integrity",
        "confidence_thesis_coherence",
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
        fair_value_population = [b.raw.get("cohort_implied_fair_value_gap") for b in group]
        for bundle in group:
            bundle.raw["cohort_quality_edge"] = percentile_rank(bundle.raw.get("active_ratio"), quality_population)
            bundle.raw["cohort_liquidity_edge"] = percentile_rank(bundle.raw.get("reserve_depth"), reserve_population)
            bundle.raw["cohort_mispricing_edge"] = percentile_rank(bundle.raw.get("price_response_lag_to_quality_shift"), change_population)
            bundle.raw["cohort_relevance_edge"] = percentile_rank(bundle.raw.get("market_relevance_proxy"), relevance_population)
            bundle.raw["cohort_fair_value_edge"] = percentile_rank(bundle.raw.get("cohort_implied_fair_value_gap"), fair_value_population)


def _inject_cohort_metrics(bundle: FeatureBundle) -> None:
    for name, category, output, weight in [
        ("cohort_quality_edge", "cohort_relative", "fundamental_quality", 0.02),
        ("cohort_liquidity_edge", "cohort_relative", "fundamental_quality", 0.02),
        ("cohort_relevance_edge", "cohort_relative", "fundamental_quality", 0.03),
        ("cohort_mispricing_edge", "cohort_relative", "mispricing_signal", 0.06),
        ("cohort_fair_value_edge", "cohort_relative", "mispricing_signal", 0.05),
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
        base_fundamental_quality = clamp01(_weighted_output(bundle, "fundamental_quality"))
        base_mispricing_signal = clamp01(_weighted_output(bundle, "mispricing_signal"))
        base_fragility_risk = clamp01(_weighted_output(bundle, "fragility_risk"))
        base_signal_confidence = clamp01(_weighted_output(bundle, "signal_confidence"))
        fragility_excess = clamp01(max(base_fragility_risk - 0.50, 0.0) / 0.50)
        yield_heat = clamp01(max((bundle.raw.get("staking_apy_proxy") or 0.0) - 60.0, 0.0) / 100.0)
        signal_fabrication_risk = clamp01(bundle.raw.get("signal_fabrication_risk") or 0.0)
        overreaction_score = clamp01(bundle.raw.get("overreaction_score") or 0.0)
        underreaction_score = clamp01(bundle.raw.get("underreaction_score") or 0.0)
        crowding_proxy = clamp01(bundle.raw.get("crowding_proxy") or 0.0)
        market_structure_floor = clamp01(bundle.raw.get("market_structure_floor") or 0.0)
        market_relevance_proxy = clamp01(bundle.raw.get("market_relevance_proxy") or 0.0)
        consensus_signal_gap = clamp01(bundle.raw.get("consensus_signal_gap") or 0.0)
        concentration_penalty = clamp01(
            max(
                bundle.raw.get("validator_dominance") or 0.0,
                bundle.raw.get("incentive_concentration") or 0.0,
            )
        )
        staking_apy_proxy = max(0.0, bundle.raw.get("staking_apy_proxy") or 0.0)
        crowded_structure_penalty = _crowded_structure_penalty(
            market_relevance=market_relevance_proxy,
            market_structure_floor=market_structure_floor,
            crowding_proxy=crowding_proxy,
            concentration=concentration_penalty,
            staking_apy=staking_apy_proxy,
        )
        quality_resolution_bonus = clamp01(
            0.45 * market_structure_floor
            + 0.30 * clamp01(bundle.raw.get("participation_breadth") or 0.0)
            + 0.25 * clamp01(bundle.raw.get("validator_participation") or 0.0)
        )
        quality_resolution_drag = clamp01(
            0.45 * concentration_penalty
            + 0.30 * crowding_proxy
            + 0.25 * yield_heat
        )
        base_fundamental_quality = clamp01(
            base_fundamental_quality
            + 0.06 * (quality_resolution_bonus - 0.50)
            - 0.05 * quality_resolution_drag
        )
        base_fragility_risk = clamp01(
            base_fragility_risk
            + 0.18 * crowded_structure_penalty
        )
        evidence_confidence = clamp01(
            0.24 * base_signal_confidence
            + 0.16 * clamp01(bundle.raw.get("data_coverage") or 0.0)
            + 0.10 * clamp01(bundle.raw.get("update_freshness") or 0.0)
            + 0.10 * (1.0 - clamp01(bundle.raw.get("proxy_reliance_penalty") or 0.0))
            + 0.08 * (1.0 - signal_fabrication_risk)
            + 0.08 * clamp01(bundle.raw.get("confidence_thesis_coherence") or 0.0)
            + 0.08 * clamp01(bundle.raw.get("low_manipulation_signal_share") or 0.0)
            + 0.08 * market_structure_floor
            + 0.08 * market_relevance_proxy
            + 0.06 * (1.0 - consensus_signal_gap)
            - 0.08 * clamp01(bundle.raw.get("low_evidence_high_conviction") or 0.0)
        )
        reflexive_confidence_drag = clamp01(
            0.38 * crowding_proxy
            + 0.22 * overreaction_score
            + 0.20 * signal_fabrication_risk
            + 0.20 * fragility_excess
        )
        structural_confidence_drag = clamp01(
            0.30 * (1.0 - market_structure_floor)
            + 0.22 * (1.0 - clamp01(bundle.raw.get("confidence_market_integrity") or 0.0))
            + 0.20 * crowding_proxy
            + 0.16 * yield_heat
            + 0.12 * fragility_excess
        )
        thesis_confidence = clamp01(
            0.24 * market_structure_floor
            + 0.22 * clamp01(bundle.raw.get("confidence_market_integrity") or 0.0)
            + 0.16 * clamp01(bundle.raw.get("confidence_thesis_coherence") or 0.0)
            + 0.12 * (1.0 - crowding_proxy)
            + 0.10 * (1.0 - overreaction_score)
            + 0.08 * (1.0 - fragility_excess)
            + 0.08 * market_relevance_proxy
            - 0.12 * yield_heat
        )
        confidence_structural_ceiling = clamp01(
            0.82
            - 0.30 * crowding_proxy
            - 0.14 * yield_heat
            - 0.14 * fragility_excess
            - 0.12 * (1.0 - market_structure_floor)
            - 0.10 * consensus_signal_gap
        )
        adjusted_thesis_confidence = clamp01(
            thesis_confidence
            * (
                1.0
                - 0.30 * reflexive_confidence_drag
                - 0.35 * structural_confidence_drag
                - 0.18 * crowded_structure_penalty
            )
        )
        adjusted_signal_confidence = min(evidence_confidence, adjusted_thesis_confidence, confidence_structural_ceiling)
        mispricing_structural_drag = _mispricing_structural_drag(
            market_structure_floor=market_structure_floor,
            market_relevance=market_relevance_proxy,
            crowding_proxy=crowding_proxy,
            overreaction_score=overreaction_score,
            signal_fabrication_risk=signal_fabrication_risk,
            fragility_excess=fragility_excess,
            yield_heat=yield_heat,
        )
        crowded_repricing_discount = _crowded_repricing_discount(
            market_relevance=market_relevance_proxy,
            market_structure_floor=market_structure_floor,
            crowding_proxy=crowding_proxy,
            underreaction_score=underreaction_score,
            overreaction_score=overreaction_score,
            fragility_excess=fragility_excess,
        )
        confidence_adjusted_mispricing = clamp01(
            base_mispricing_signal
            * (0.25 + 0.75 * adjusted_signal_confidence)
            * (1.0 - 0.60 * mispricing_structural_drag)
            * (1.0 - 0.70 * crowded_repricing_discount)
            - 0.24 * signal_fabrication_risk
            - 0.10 * overreaction_score
            - 0.22 * crowded_repricing_discount
        )
        confidence_adjusted_thesis_strength = clamp01(
            0.45 * base_fundamental_quality
            + 0.35 * confidence_adjusted_mispricing
            + 0.20 * adjusted_signal_confidence
        )
        bundle.raw["base_mispricing_signal"] = base_mispricing_signal
        bundle.raw["base_signal_confidence"] = base_signal_confidence
        bundle.raw["crowded_structure_penalty"] = crowded_structure_penalty
        bundle.raw["quality_resolution_bonus"] = quality_resolution_bonus
        bundle.raw["quality_resolution_drag"] = quality_resolution_drag
        bundle.raw["evidence_confidence"] = evidence_confidence
        bundle.raw["thesis_confidence"] = thesis_confidence
        bundle.raw["reflexive_confidence_drag"] = reflexive_confidence_drag
        bundle.raw["structural_confidence_drag"] = structural_confidence_drag
        bundle.raw["confidence_structural_ceiling"] = confidence_structural_ceiling
        bundle.raw["adjusted_thesis_confidence"] = adjusted_thesis_confidence
        bundle.raw["adjusted_signal_confidence"] = adjusted_signal_confidence
        bundle.raw["mispricing_structural_drag"] = mispricing_structural_drag
        bundle.raw["crowded_repricing_discount"] = crowded_repricing_discount
        bundle.raw["confidence_adjusted_mispricing"] = confidence_adjusted_mispricing
        bundle.raw["confidence_adjusted_thesis_strength"] = confidence_adjusted_thesis_strength
        primary = PrimarySignals(
            fundamental_quality=base_fundamental_quality,
            mispricing_signal=confidence_adjusted_mispricing,
            fragility_risk=base_fragility_risk,
            signal_confidence=adjusted_signal_confidence,
        )
        bundle.primary_signals = primary
        bundle.axes = _legacy_axes_from_primary(primary, bundle)
    return raw_bundles
