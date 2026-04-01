import math
from collections import defaultdict
from datetime import datetime
from statistics import fmean
from typing import Iterable

from collectors.models import HistoricalFeaturePoint, RawSubnetSnapshot
from features.components_confidence import build_confidence_components
from features.components_fragility import build_fragility_components
from features.components_opportunity import build_opportunity_components
from features.components_quality import build_quality_components
from features.conditioning import condition_snapshot
from features.normalization import clamp01, log_scaled, normalize_metric_value
from features.types import AxisScores, FeatureBundle, FeatureMetric, PrimarySignals
from scorer.normalizer import percentile_rank


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


def _freshness(snapshot_like: dict[str, object], lookback_blocks: int) -> float:
    last_update_blocks = snapshot_like.get("last_update_blocks") or []
    current_block = int(snapshot_like.get("current_block") or 0)
    if not last_update_blocks:
        return 0.0
    ages = [max(current_block - int(block), 0) for block in last_update_blocks if block is not None]
    if not ages:
        return 0.0
    recent_share = safe_ratio(sum(1 for age in ages if age <= lookback_blocks), len(ages))
    median_age = sorted(ages)[len(ages) // 2]
    age_decay = math.exp(-safe_ratio(median_age, max(lookback_blocks * 1.5, 1)))
    coverage = safe_ratio(
        len(ages),
        max(int(snapshot_like.get("yuma_neurons") or snapshot_like.get("n_total") or len(ages)), 1),
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
        safe_ratio(sum(1 for point in history if getattr(point, field) is not None), len(history))
        for field in expected_fields
    ]
    avg_field_presence = fmean(field_presence) if field_presence else 0.0
    parsed_timestamps = [dt for dt in (_parse_iso_timestamp(point.timestamp) for point in history) if dt is not None]
    unique_days = len({dt.date() for dt in parsed_timestamps})
    point_depth = clamp01(len(history) / 18.0)
    time_depth = clamp01(unique_days / 14.0)
    return clamp01(0.40 * point_depth + 0.35 * avg_field_presence + 0.25 * time_depth)


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
        candidates = [value for value in (point.intrinsic_quality, point.economic_sustainability) if value is not None]
        if candidates:
            series.append(float(fmean(candidates)))
    return series


def _current_quality_state(
    active_ratio: float,
    participation_breadth: float,
    validator_participation: float,
    incentive_distribution_quality: float,
    market_structure_floor: float,
) -> float:
    return clamp01(
        fmean(
            [
                active_ratio,
                participation_breadth,
                validator_participation,
                incentive_distribution_quality,
                market_structure_floor,
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


def _trend_slope(history: list[float], periods: int = 4) -> float | None:
    if len(history) < 2:
        return None
    sample = history[-periods:]
    if len(sample) < 2:
        return None
    return (sample[-1] - sample[0]) / max(len(sample) - 1, 1)


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


def _history_anchor(history: list[float], fallback: float = 0.0) -> float:
    if not history:
        return fallback
    return history[-1]


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
    reserve_score = log_scaled(reserve_depth, 200_000)
    return clamp01(fmean([reserve_score, active_ratio, participation_breadth, validator_participation]))


def _effective_participant_share(values: Iterable[float], expected_count: int) -> float:
    clean = [float(v) for v in values if v > 0]
    if not clean:
        return 0.0
    effective_count = 1.0 / max(herfindahl(clean), 1e-9)
    reference_count = max(2.0, min(float(expected_count), 24.0))
    return clamp01((effective_count - 1.0) / max(reference_count - 1.0, 1.0))


def _structural_absorption(
    participation_breadth: float,
    validator_participation: float,
    market_structure_floor: float,
    market_relevance: float,
) -> float:
    return clamp01(
        0.32 * market_structure_floor
        + 0.24 * market_relevance
        + 0.24 * participation_breadth
        + 0.20 * validator_participation
    )


def _contextualize_concentration(
    raw_concentration: float,
    participation_breadth: float,
    validator_participation: float,
    market_structure_floor: float,
    market_relevance: float,
) -> float:
    absorption = _structural_absorption(
        participation_breadth=participation_breadth,
        validator_participation=validator_participation,
        market_structure_floor=market_structure_floor,
        market_relevance=market_relevance,
    )
    return clamp01(raw_concentration * (1.0 - 0.42 * absorption))


def _incentive_distribution_quality(
    incentive_scores: Iterable[float],
    participation_breadth: float,
    validator_participation: float,
) -> tuple[float, float]:
    clean = [float(v) for v in incentive_scores if v > 0]
    if not clean:
        return 0.0, 1.0
    total = sum(clean)
    max_share = max(clean) / total if total > 0 else 1.0
    raw_concentration = herfindahl(clean)
    gini_quality = 1.0 - gini(clean)
    entropy_quality = normalized_entropy(clean)
    effective_share = _effective_participant_share(clean, len(clean))
    breadth_support = math.sqrt(clamp01(0.60 * participation_breadth + 0.40 * validator_participation))
    tail_balance = 1.0 - clamp01(max_share)
    quality = clamp01(
        0.24 * gini_quality
        + 0.18 * entropy_quality
        + 0.18 * effective_share
        + 0.14 * tail_balance
        + 0.26 * breadth_support
    )
    return quality, raw_concentration


def _validator_dominance_score(
    validator_stakes: list[float],
    top3_stake_fraction: float,
    n_validators: int,
    participation_breadth: float,
    validator_participation: float,
    market_structure_floor: float,
    market_relevance: float,
) -> tuple[float, float]:
    clean = [float(v) for v in validator_stakes if v > 0]
    if not clean:
        return 1.0, 1.0
    total = sum(clean)
    validator_count = max(n_validators, len(clean), 1)
    top1_share = max(clean) / total if total > 0 else 1.0
    baseline_top1 = 1.0 / validator_count
    baseline_top3 = min(1.0, 3.0 / validator_count)
    top1_excess = clamp01((top1_share - baseline_top1) / max(1.0 - baseline_top1, 1e-9))
    top3_excess = clamp01((top3_stake_fraction - baseline_top3) / max(1.0 - baseline_top3, 1e-9))
    raw_dominance = clamp01(0.58 * top1_excess + 0.42 * top3_excess)
    adjusted_dominance = _contextualize_concentration(
        raw_concentration=raw_dominance,
        participation_breadth=participation_breadth,
        validator_participation=validator_participation,
        market_structure_floor=market_structure_floor,
        market_relevance=market_relevance,
    )
    return adjusted_dominance, raw_dominance


def _market_structure_floor(
    reserve_depth: float,
    liquidity_thinness: float | None,
    active_ratio: float,
    participation_breadth: float,
    validator_participation: float,
) -> float:
    reserve_score = log_scaled(reserve_depth, 50_000)
    liquidity_score = clamp01(1.0 - min(1.0, liquidity_thinness or 0.0))
    return clamp01(fmean([reserve_score, liquidity_score, active_ratio, participation_breadth, validator_participation]))


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


def _crowded_expectation_saturation(
    market_relevance: float,
    crowding_proxy: float,
    realized_price_level: float,
) -> float:
    return clamp01(0.45 * market_relevance + 0.35 * crowding_proxy + 0.20 * realized_price_level)


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
    conditioned = condition_snapshot(snapshot)
    c = conditioned.values
    yuma_neurons = c["yuma_neurons"] or c["n_total"] or 1
    validator_reference = max(4.0, min(16.0, math.sqrt(max(yuma_neurons, 1))))
    has_validator_activity_basis = c["active_validators_7d"] is not None and c["n_validators"] > 0
    active_ratio = safe_ratio(
        c["active_validators_7d"] if has_validator_activity_basis else c["active_neurons_7d"],
        c["n_validators"] if has_validator_activity_basis else yuma_neurons,
    )
    participation_breadth = safe_ratio(c["unique_coldkeys"], max(c["n_total"], 1))
    validator_participation = clamp01(c["n_validators"] / validator_reference)
    validator_weight_entropy = (
        fmean(normalized_entropy(row) for row in c["validator_weight_matrix"])
        if c["validator_weight_matrix"] else None
    )
    cross_validator_disagreement = (
        mean_pairwise_l1(c["validator_weight_matrix"])
        if c["validator_weight_matrix"] else None
    )
    meaningful_discrimination = (
        fmean(1.0 - normalized_entropy(row) for row in c["validator_weight_matrix"])
        if c["validator_weight_matrix"] else None
    )
    bond_responsiveness = (
        fmean(1.0 - normalized_entropy(row) for row in c["validator_bond_matrix"])
        if c["validator_bond_matrix"] else None
    )
    slippage_1 = simulate_tao_buy_slippage(c["tao_in_pool"], c["alpha_in_pool"], 1.0)
    slippage_10 = simulate_tao_buy_slippage(c["tao_in_pool"], c["alpha_in_pool"], 10.0)
    slippage_50 = simulate_tao_buy_slippage(c["tao_in_pool"], c["alpha_in_pool"], 50.0)
    avg_slippage = (
        fmean(v for v in [slippage_1, slippage_10, slippage_50] if v is not None)
        if any(v is not None for v in [slippage_1, slippage_10, slippage_50]) else None
    )
    market_relevance = _market_relevance_proxy(c["tao_in_pool"], active_ratio, participation_breadth, validator_participation)
    market_structure_floor = _market_structure_floor(c["tao_in_pool"], avg_slippage, active_ratio, participation_breadth, validator_participation)
    incentive_distribution_quality, raw_incentive_concentration = _incentive_distribution_quality(
        c["incentive_scores"],
        participation_breadth=participation_breadth,
        validator_participation=validator_participation,
    )
    incentive_concentration = _contextualize_concentration(
        raw_concentration=raw_incentive_concentration,
        participation_breadth=participation_breadth,
        validator_participation=validator_participation,
        market_structure_floor=market_structure_floor,
        market_relevance=market_relevance,
    )
    validator_dominance, raw_validator_dominance = _validator_dominance_score(
        c["validator_stakes"],
        c["top3_stake_fraction"],
        c["n_validators"],
        participation_breadth=participation_breadth,
        validator_participation=validator_participation,
        market_structure_floor=market_structure_floor,
        market_relevance=market_relevance,
    )
    concentration_now = max(validator_dominance, incentive_concentration)
    history = c["history"] or []
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
    quality_current = _current_quality_state(
        active_ratio,
        participation_breadth,
        validator_participation,
        incentive_distribution_quality,
        market_structure_floor,
    )
    price_change = _change_vs_history(c["alpha_price_tao"], price_history)
    active_change = _change_vs_history(active_ratio, active_history)
    breadth_change = _change_vs_history(participation_breadth, breadth_history)
    validator_change = _change_vs_history(validator_participation, validator_history)
    structure_change = _change_vs_history(market_structure_floor, structure_history)
    quality_change = _change_vs_history(quality_current, quality_history)
    emission_change = _change_vs_history(c["emission_per_block_tao"], emission_history)
    reserve_change = _change_vs_history(c["tao_in_pool"], flow_history)
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
    validator_diversity_trend = None if concentration_change is None else -concentration_change
    price_response_lag_to_quality_shift = max(0.0, max(quality_change or 0.0, quality_acceleration or 0.0) - max(price_change or 0.0, 0.0))
    emission_to_sticky_usage_conversion = max(
        0.0,
        0.50 * max(active_change or 0.0, 0.0)
        + 0.25 * max(breadth_change or 0.0, 0.0)
        + 0.25 * max(structure_change or 0.0, 0.0)
        - max(emission_change or 0.0, 0.0),
    )
    post_incentive_retention = max(
        0.0,
        0.45 * emission_to_sticky_usage_conversion
        + 0.30 * max(quality_change or 0.0, 0.0)
        + 0.25 * max(structure_change or 0.0, 0.0)
        - 0.40 * max(price_change or 0.0, 0.0),
    )
    reserve_growth_without_price = max(0.0, (reserve_change or 0.0) - max(price_change or 0.0, 0.0))
    participation_without_crowding = max(
        0.0,
        0.50 * max(active_change or 0.0, 0.0)
        + 0.30 * max(breadth_change or 0.0, 0.0)
        + 0.20 * max(validator_diversity_trend or 0.0, 0.0),
    )
    reversal_risk = max(0.0, (price_change or 0.0) - max(quality_change or 0.0, 0.0))
    crowding_proxy = clamp01(
        0.45 * concentration_now
        + 0.25 * clamp01(avg_slippage or 0.0)
        + 0.30 * clamp01(max(price_change or 0.0, 0.0))
    )
    staking_apy_proxy = 0.0
    if c["tao_in_pool"] > 0:
        staking_apy_proxy = max(0.0, c["emission_per_block_tao"] * 7200 * 365 / c["tao_in_pool"] * 100)
    dereg_risk_proxy = clamp01(
        0.45 * max(0.0, 0.35 - active_ratio)
        + 0.25 * max(0.0, 0.20 - participation_breadth)
        + 0.20 * concentration_now
        + 0.10 * (1.0 if c["registration_allowed"] else 0.0)
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
        max(0.0, (emission_change or 0.0) - max(active_change or 0.0, 0.0)),
        flow_to_price_elasticity,
    )
    freshness = _freshness(c, lookback_blocks=7200)
    history_depth_score = _history_depth_score(history)
    validator_signal_coverage = _signal_presence_ratio(
        [validator_weight_entropy, cross_validator_disagreement, meaningful_discrimination, bond_responsiveness]
    )
    market_signal_coverage = _signal_presence_ratio(
        [slippage_1, slippage_10, slippage_50, avg_slippage, c["alpha_price_tao"], c["tao_in_pool"], c["alpha_in_pool"]]
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
            float(c["github"].commits_30d) if c["github"] else None,
            float(c["github"].contributors_30d) if c["github"] else None,
            1.0 if c["github"] and c["github"].last_push else None,
        ]
    )
    data_coverage = clamp01(
        0.35 * market_signal_coverage
        + 0.30 * history_signal_coverage
        + 0.15 * external_evidence_coverage
        + 0.20 * validator_signal_coverage
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
    realized_price_level = percentile_rank(c["alpha_price_tao"], price_history + [c["alpha_price_tao"]])
    crowded_expectation_saturation = _crowded_expectation_saturation(
        market_relevance=market_relevance,
        crowding_proxy=crowding_proxy,
        realized_price_level=realized_price_level,
    )
    raw_cohort_implied_fair_value_gap = fair_value_anchor - realized_price_level
    cohort_implied_fair_value_gap = (
        max(raw_cohort_implied_fair_value_gap, 0.0) * (1.0 - 0.45 * crowded_expectation_saturation)
        - max(-raw_cohort_implied_fair_value_gap, 0.0)
    )
    raw_underreaction_score = clamp01(
        0.45 * max(expected_price_response_gap, 0.0)
        + 0.30 * max(expected_reserve_response_gap, 0.0)
        + 0.25 * max(cohort_implied_fair_value_gap, 0.0)
    )
    underreaction_score = clamp01(raw_underreaction_score * (1.0 - 0.35 * crowded_expectation_saturation))
    overreaction_score = clamp01(
        0.50 * max(realized_price_response - expected_price_response, 0.0)
        + 0.30 * max(realized_price_level - fair_value_anchor, 0.0)
        + 0.20 * reversal_risk
    )
    market_data_reliability = conditioned.reliability.get("market_data_reliability", 0.0)
    validator_data_reliability = conditioned.reliability.get("validator_data_reliability", 0.0)
    history_data_reliability = conditioned.reliability.get("history_data_reliability", 0.0)
    external_data_reliability = conditioned.reliability.get("external_data_reliability", 0.0)
    onchain_evidence_support = clamp01(
        0.35 * market_structure_floor
        + 0.25 * market_relevance
        + 0.20 * (1.0 - concentration_now)
        + 0.20 * market_data_reliability
    )
    proxy_reliance_penalty = clamp01(
        (
            0.25 * (1.0 - freshness)
            + 0.20 * (1.0 - history_depth_score)
            + 0.15 * (1.0 - data_coverage)
            + 0.15 * (1.0 - market_data_reliability)
            + 0.15 * (1.0 - validator_data_reliability)
            + 0.10 * consensus_signal_gap
        )
        * (1.0 - 0.45 * onchain_evidence_support)
    )
    low_manipulation_signal_share = clamp01(
        0.22 * freshness
        + 0.20 * (1.0 - concentration_now)
        + 0.20 * market_structure_floor
        + 0.18 * market_relevance
        + 0.10 * data_coverage
        + 0.10 * market_data_reliability
    )
    signal_fabrication_risk = clamp01(
        0.30 * proxy_reliance_penalty
        + 0.20 * (1.0 - data_coverage)
        + 0.15 * consensus_signal_gap
        + 0.15 * (1.0 - confidence_thesis_coherence)
        + 0.10 * overreaction_score
        + 0.10 * crowding_proxy
        - 0.12 * low_manipulation_signal_share
        - 0.08 * market_structure_floor
    )
    low_evidence_high_conviction = clamp01(
        0.50 * signal_fabrication_risk
        + 0.30 * max(underreaction_score - data_coverage, 0.0)
        + 0.20 * max(underreaction_score - confidence_thesis_coherence, 0.0)
    )
    raw = {
        "active_ratio": active_ratio,
        "participation_breadth": participation_breadth,
        "validator_participation": validator_participation,
        "incentive_distribution_quality": incentive_distribution_quality,
        "incentive_distribution_quality_raw": 1.0 - gini(c["incentive_scores"]),
        "update_freshness": freshness,
        "validator_weight_entropy": validator_weight_entropy,
        "cross_validator_disagreement": cross_validator_disagreement,
        "meaningful_discrimination": meaningful_discrimination,
        "bond_responsiveness": bond_responsiveness,
        "incentive_concentration": incentive_concentration,
        "incentive_concentration_raw": raw_incentive_concentration,
        "validator_dominance": validator_dominance,
        "validator_dominance_raw": raw_validator_dominance,
        "concentration": concentration_now,
        "structural_concentration_risk": concentration_now,
        "reserve_depth": c["tao_in_pool"],
        "alpha_reserve": c["alpha_in_pool"],
        "tao_reserve": c["tao_in_pool"],
        "slippage_1_tao": slippage_1,
        "slippage_10_tao": slippage_10,
        "slippage_50_tao": slippage_50,
        "liquidity_thinness": avg_slippage,
        "emission_efficiency": safe_ratio(c["total_stake_tao"], max(c["emission_per_block_tao"], 1e-9)),
        "emission_concentration": incentive_concentration,
        "emission_persistence": _persistence(emission_history),
        "flow_stability": _persistence(flow_history),
        "flow_to_price_elasticity": clamp01(flow_to_price_elasticity),
        "price_move_without_quality_improvement": max(0.0, (price_change or 0.0) - max(quality_change or 0.0, 0.0)),
        "emission_spike_without_participation_improvement": max(0.0, (emission_change or 0.0) - max(active_change or 0.0, 0.0)),
        "reserve_sensitivity": avg_slippage,
        "crowding_proxy": crowding_proxy,
        "sharp_short_term_reversal_risk": reversal_risk,
        "performance_driven_by_few_actors": concentration_now,
        "market_relevance_proxy": market_relevance,
        "confidence_market_relevance": market_relevance,
        "market_structure_floor": market_structure_floor,
        "confidence_market_structure_floor": market_structure_floor,
        "staking_apy_proxy": staking_apy_proxy,
        "registration_openness": 1.0 if c["registration_allowed"] else 0.0,
        "pow_registration_enabled": 1.0 if c["difficulty"] > 0 else 0.0,
        "burn_registration_enabled": 1.0 if c["min_burn"] > 0 or c["max_burn"] > 0 else 0.0,
        "immunity_period": float(c["immunity_period"]),
        "dereg_risk_proxy": dereg_risk_proxy,
        "repo_commits_30d": float(c["github"].commits_30d) if c["github"] else None,
        "repo_contributors_30d": float(c["github"].contributors_30d) if c["github"] else None,
        "repo_recency": None if not c["github"] or not c["github"].last_push else 1.0,
        "confidence_market_integrity": confidence_market_integrity,
        "confidence_thesis_coherence": confidence_thesis_coherence,
        "quality_change": quality_change,
        "reserve_change": reserve_change,
        "price_change": price_change,
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
        "market_data_reliability": market_data_reliability,
        "validator_data_reliability": validator_data_reliability,
        "history_data_reliability": history_data_reliability,
        "external_data_reliability": external_data_reliability,
        "conditioning_original_fields": float(len(conditioned.visibility["original"])),
        "conditioning_bounded_fields": float(len(conditioned.visibility["bounded"])),
        "conditioning_reconstructed_fields": float(len(conditioned.visibility["reconstructed"])),
        "conditioning_discarded_fields": float(len(conditioned.visibility["discarded"])),
    }
    return FeatureBundle(raw=raw, conditioned=conditioned)


METRIC_MAP = {
    "active_ratio": ("direct_onchain", "fundamental_quality", 0.10, False),
    "participation_breadth": ("direct_onchain", "fundamental_quality", 0.10, False),
    "validator_participation": ("direct_onchain", "fundamental_quality", 0.08, False),
    "incentive_distribution_quality": ("derived_onchain", "fundamental_quality", 0.08, False),
    "reserve_depth": ("direct_onchain", "fundamental_quality", 0.08, False),
    "market_relevance_proxy": ("derived_onchain", "fundamental_quality", 0.06, False),
    "market_structure_floor": ("derived_onchain", "fundamental_quality", 0.08, False),
    "concentration": ("derived_onchain", "fragility_risk", 0.10, True),
    "validator_weight_entropy": ("derived_onchain", "fundamental_quality", 0.0, False),
    "cross_validator_disagreement": ("derived_onchain", "fundamental_quality", 0.0, True),
    "meaningful_discrimination": ("derived_onchain", "fundamental_quality", 0.0, False),
    "bond_responsiveness": ("derived_onchain", "fundamental_quality", 0.0, False),
    "slippage_10_tao": ("simulated", "fragility_risk", 0.08, True),
    "slippage_50_tao": ("simulated", "fragility_risk", 0.10, True),
    "liquidity_thinness": ("simulated", "fragility_risk", 0.10, False),
    "emission_efficiency": ("derived_onchain", "fundamental_quality", 0.05, False),
    "flow_to_price_elasticity": ("needs_history", "fragility_risk", 0.06, True),
    "price_move_without_quality_improvement": ("needs_history", "fragility_risk", 0.08, False),
    "emission_spike_without_participation_improvement": ("needs_history", "fragility_risk", 0.05, False),
    "crowding_proxy": ("derived_onchain", "fragility_risk", 0.08, False),
    "sharp_short_term_reversal_risk": ("needs_history", "fragility_risk", 0.08, False),
    "quality_change": ("needs_history", "mispricing_signal", 0.10, False),
    "reserve_change": ("needs_history", "mispricing_signal", 0.08, False),
    "quality_acceleration": ("needs_history", "mispricing_signal", 0.10, False),
    "liquidity_improvement_rate": ("needs_history", "mispricing_signal", 0.08, False),
    "validator_diversity_trend": ("needs_history", "mispricing_signal", 0.06, False),
    "expected_price_response_gap": ("needs_history", "mispricing_signal", 0.12, False),
    "expected_reserve_response_gap": ("needs_history", "mispricing_signal", 0.08, False),
    "cohort_implied_fair_value_gap": ("cohort_relative", "mispricing_signal", 0.10, False),
    "underreaction_score": ("needs_history", "mispricing_signal", 0.12, False),
    "overreaction_score": ("needs_history", "mispricing_signal", 0.08, True),
    "price_response_lag_to_quality_shift": ("needs_history", "mispricing_signal", 0.14, False),
    "emission_to_sticky_usage_conversion": ("needs_history", "mispricing_signal", 0.10, False),
    "post_incentive_retention": ("needs_history", "mispricing_signal", 0.10, False),
    "reserve_growth_without_price": ("needs_history", "mispricing_signal", 0.08, False),
    "participation_without_crowding": ("needs_history", "mispricing_signal", 0.08, False),
    "data_coverage": ("derived_onchain", "signal_confidence", 0.12, False),
    "consensus_signal_gap": ("derived_onchain", "signal_confidence", 0.10, True),
    "history_depth_score": ("needs_history", "signal_confidence", 0.12, False),
    "proxy_reliance_penalty": ("derived_onchain", "signal_confidence", 0.10, True),
    "low_manipulation_signal_share": ("derived_onchain", "signal_confidence", 0.08, False),
    "confidence_market_integrity": ("derived_onchain", "signal_confidence", 0.10, False),
    "confidence_thesis_coherence": ("needs_history", "signal_confidence", 0.10, False),
    "signal_fabrication_risk": ("derived_onchain", "signal_confidence", 0.08, True),
    "market_data_reliability": ("conditioning", "signal_confidence", 0.08, False),
    "validator_data_reliability": ("conditioning", "signal_confidence", 0.08, False),
    "history_data_reliability": ("conditioning", "signal_confidence", 0.08, False),
    "external_data_reliability": ("conditioning", "signal_confidence", 0.04, False),
    "repo_commits_30d": ("external_proxy", "signal_confidence", 0.02, False),
    "repo_contributors_30d": ("external_proxy", "signal_confidence", 0.02, False),
    "repo_recency": ("external_proxy", "signal_confidence", 0.02, False),
}


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
        ("cohort_mispricing_edge", "cohort_relative", "mispricing_signal", 0.05),
        ("cohort_fair_value_edge", "cohort_relative", "mispricing_signal", 0.05),
        ("cohort_relevance_edge", "cohort_relative", "signal_confidence", 0.03),
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


def _legacy_axes_from_primary(primary: PrimarySignals, bundle: FeatureBundle) -> AxisScores:
    intrinsic = clamp01(0.82 * primary.fundamental_quality + 0.18 * (bundle.raw.get("cohort_quality_edge") or 0.0))
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


def _compose_score(parts: list[tuple[str, float, float, str, str]]) -> tuple[float, list[dict]]:
    total_weight = sum(weight for _, _, weight, _, _ in parts) or 1.0
    score = sum(value * weight for _, value, weight, _, _ in parts) / total_weight
    contributions = []
    for name, value, weight, source_block, explanation in parts:
        signed = ((value - 0.5) * weight) / total_weight
        direction = "positive" if signed > 0 else "negative" if signed < 0 else "neutral"
        contributions.append(
            {
                "name": name,
                "signed_contribution": round(signed, 4),
                "direction": direction,
                "short_explanation": explanation,
                "source_block": source_block,
            }
        )
    return clamp01(score), contributions


def normalize_features(raw_bundles: list[FeatureBundle]) -> list[FeatureBundle]:
    _build_cohort_edges(raw_bundles)
    all_values = {key: [bundle.raw.get(key) for bundle in raw_bundles] for key in METRIC_MAP}
    for bundle in raw_bundles:
        metrics: dict[str, FeatureMetric] = {}
        normalized: dict[str, float] = {}
        for key, (category, output, weight, inverse) in METRIC_MAP.items():
            value = bundle.raw.get(key)
            normalized_value = normalize_metric_value(key, value, all_values[key])
            normalized[key] = normalized_value
            metrics[key] = FeatureMetric(
                name=key,
                value=value,
                normalized=normalized_value,
                category=category,
                axis=output,
                weight=weight,
                higher_is_better=not inverse,
            )
        bundle.metrics = metrics
        _inject_cohort_metrics(bundle)
        base_components = build_quality_components(bundle.raw, normalized)
        opportunity_components = build_opportunity_components(bundle.raw, normalized)
        fragility_components = build_fragility_components(bundle.raw, normalized, base_components)
        confidence_components = build_confidence_components(bundle.raw, normalized, base_components, opportunity_components, fragility_components)
        market_legitimacy = clamp01(
            0.40 * base_components["market_relevance"]
            + 0.35 * base_components["liquidity_health"]
            + 0.25 * base_components["concentration_health"]
        )
        fundamental_health, fundamental_contribs = _compose_score(
            [
                ("participation_health", base_components["participation_health"], 0.22, "base_components", "Breadth and live participation remain structurally healthy."),
                ("validator_health", base_components["validator_health"], 0.20, "base_components", "Validator participation and signal quality remain supportive."),
                ("liquidity_health", base_components["liquidity_health"], 0.22, "base_components", "Reserve depth and executable liquidity support durability."),
                ("concentration_health", base_components["concentration_health"], 0.18, "base_components", "Ownership is not overly concentrated."),
                ("market_relevance", base_components["market_relevance"], 0.18, "base_components", "The subnet has enough economic relevance for the thesis to matter."),
            ]
        )
        opportunity_underreaction, opportunity_contribs = _compose_score(
            [
                ("quality_momentum", opportunity_components["quality_momentum"], 0.24, "base_components", "Quality is improving faster than a flat thesis would imply."),
                ("reserve_momentum", opportunity_components["reserve_momentum"], 0.20, "base_components", "Reserve depth is improving on a real rather than purely price-led basis."),
                ("price_lag", opportunity_components["price_lag"], 0.22, "base_components", "Price still lags the observed operational improvement."),
                ("uncrowded_participation", opportunity_components["uncrowded_participation"], 0.16, "base_components", "Participation is improving without an equally crowded setup."),
                ("fair_value_gap_light", opportunity_components["fair_value_gap_light"], 0.18, "base_components", "A light fair-value gap remains visible after saturation checks."),
            ]
        )
        fragility_block, fragility_contribs = _compose_score(
            [
                ("crowding_level", fragility_components["crowding_level"], 0.24, "base_components", "Crowding raises reflexive downside risk."),
                ("concentration_risk", fragility_components["concentration_risk"], 0.24, "base_components", "Concentration still leaves the structure vulnerable."),
                ("thin_liquidity_risk", fragility_components["thin_liquidity_risk"], 0.22, "base_components", "Liquidity remains thin for larger flows."),
                ("reversal_risk", fragility_components["reversal_risk"], 0.18, "base_components", "Recent price action is vulnerable to reversal."),
                ("weak_market_structure", fragility_components["weak_market_structure"], 0.12, "base_components", "Market structure is not yet fully self-supporting."),
            ]
        )
        evidence_confidence, evidence_contribs = _compose_score(
            [
                ("data_confidence", confidence_components["data_confidence"], 0.40, "base_components", "Conditioned inputs and telemetry quality support the reading."),
                ("market_confidence", confidence_components["market_confidence"], 0.30, "base_components", "Market structure is strong enough for the signal to be actionable."),
                ("thesis_confidence", confidence_components["thesis_confidence"], 0.30, "base_components", "The improvement thesis is coherent and not purely reflexive."),
            ]
        )
        concentration_penalty = clamp01(max(bundle.raw.get("validator_dominance") or 0.0, bundle.raw.get("incentive_concentration") or 0.0))
        crowded_structure_penalty = clamp01(
            0.35 * fragility_components["crowding_level"]
            + 0.30 * concentration_penalty
            + 0.20 * fragility_components["thin_liquidity_risk"]
            + 0.15 * clamp01(max((bundle.raw.get("staking_apy_proxy") or 0.0) - 90.0, 0.0) / 120.0)
        )
        quality_resolution_bonus = clamp01(
            0.45 * base_components["liquidity_health"]
            + 0.30 * base_components["participation_health"]
            + 0.25 * base_components["validator_health"]
        )
        small_structural_penalty = clamp01(
            0.55 * max(concentration_penalty - 0.75, 0.0) / 0.25
            + 0.45 * max(fragility_components["thin_liquidity_risk"] - 0.75, 0.0) / 0.25
        )
        fundamental_quality = clamp01(
            0.86 * fundamental_health
            + 0.14 * market_legitimacy
            + 0.04 * (quality_resolution_bonus - 0.5)
            - 0.10 * small_structural_penalty
        )
        confidence_factor = clamp01(0.45 + 0.55 * (0.55 * confidence_components["data_confidence"] + 0.45 * confidence_components["thesis_confidence"]))
        structural_validity_factor = clamp01(
            0.35 * confidence_components["market_confidence"]
            + 0.25 * (1.0 - fragility_block)
            + 0.20 * base_components["liquidity_health"]
            + 0.20 * base_components["market_relevance"]
        )
        extreme_crowding_penalty = clamp01(max(fragility_components["crowding_level"] - 0.70, 0.0) / 0.30)
        obvious_overreaction_penalty = clamp01(max((bundle.raw.get("overreaction_score") or 0.0) - 0.20, 0.0) / 0.80)
        low_legitimacy_penalty = clamp01(max(0.45 - market_legitimacy, 0.0) / 0.45)
        small_penalties = clamp01(0.40 * obvious_overreaction_penalty + 0.35 * extreme_crowding_penalty + 0.25 * low_legitimacy_penalty)
        mispricing_signal = clamp01(opportunity_underreaction * confidence_factor * structural_validity_factor - 0.16 * small_penalties)
        signal_confidence = clamp01(
            (
                0.40 * confidence_components["data_confidence"]
                + 0.30 * confidence_components["market_confidence"]
                + 0.30 * confidence_components["thesis_confidence"]
            )
            * (0.75 + 0.25 * confidence_components["evidence_depth"])
        )
        confidence_structural_ceiling = clamp01(
            0.84
            - 0.26 * fragility_components["crowding_level"]
            - 0.22 * fragility_components["thin_liquidity_risk"]
            - 0.16 * concentration_penalty
            - 0.10 * normalized.get("consensus_signal_gap", 0.0)
            - 0.12 * crowded_structure_penalty
        )
        adjusted_thesis_confidence = clamp01(
            confidence_components["thesis_confidence"]
            * (
                1.0
                - 0.20 * fragility_components["crowding_level"]
                - 0.16 * fragility_components["thin_liquidity_risk"]
                - 0.12 * concentration_penalty
                - 0.10 * crowded_structure_penalty
            )
        )
        evidence_confidence = min(evidence_confidence, confidence_structural_ceiling)
        adjusted_signal_confidence = min(signal_confidence, confidence_structural_ceiling, adjusted_thesis_confidence, evidence_confidence)
        signal_confidence = adjusted_signal_confidence
        thesis_strength = clamp01(
            0.42 * fundamental_quality
            + 0.33 * mispricing_signal
            + 0.15 * signal_confidence
            + 0.10 * (1.0 - fragility_block)
        )
        bundle.base_components = {**base_components, **opportunity_components, **fragility_components, **confidence_components}
        crowded_structure_watchlist = clamp01(
            0.35 * fragility_components["crowding_level"]
            + 0.30 * concentration_penalty
            + 0.20 * fragility_components["thin_liquidity_risk"]
            + 0.15 * clamp01(max((bundle.raw.get("staking_apy_proxy") or 0.0) - 90.0, 0.0) / 120.0)
        )
        bundle.core_blocks = {
            "fundamental_health": fundamental_health,
            "opportunity_underreaction": opportunity_underreaction,
            "fragility": fragility_block,
            "evidence_confidence": evidence_confidence,
            "market_legitimacy": market_legitimacy,
            "confidence_factor": confidence_factor,
            "structural_validity": structural_validity_factor,
            "crowded_structure_watchlist": crowded_structure_watchlist,
        }
        bundle.ranking = {
            "resilience": clamp01(1.0 - fragility_block),
            "market_relevance": base_components["market_relevance"],
            "thesis_strength": thesis_strength,
        }
        bundle.contributions = {
            "fundamental_health": fundamental_contribs,
            "opportunity_underreaction": opportunity_contribs,
            "fragility": fragility_contribs,
            "evidence_confidence": evidence_contribs,
            "fundamental_quality": [
                {"name": "fundamental_health", "signed_contribution": round((fundamental_health - 0.5) * 0.86, 4), "direction": "positive" if fundamental_health >= 0.5 else "negative", "short_explanation": "Structural health is the dominant driver of fundamental quality.", "source_block": "core_blocks"},
                {"name": "market_legitimacy", "signed_contribution": round((market_legitimacy - 0.5) * 0.14, 4), "direction": "positive" if market_legitimacy >= 0.5 else "negative", "short_explanation": "Market legitimacy modestly lifts or caps the quality score.", "source_block": "core_blocks"},
            ],
            "mispricing_signal": [
                {"name": "base_opportunity", "signed_contribution": round((opportunity_underreaction - 0.5) * 0.5, 4), "direction": "positive" if opportunity_underreaction >= 0.5 else "negative", "short_explanation": "Observed underreaction forms the base opportunity.", "source_block": "core_blocks"},
                {"name": "confidence_factor", "signed_contribution": round((confidence_factor - 0.5) * 0.25, 4), "direction": "positive" if confidence_factor >= 0.5 else "negative", "short_explanation": "Data and thesis confidence scale the opportunity rather than replacing it.", "source_block": "core_blocks"},
                {"name": "structural_validity_factor", "signed_contribution": round((structural_validity_factor - 0.5) * 0.25, 4), "direction": "positive" if structural_validity_factor >= 0.5 else "negative", "short_explanation": "Market structure validates whether the opportunity is investable.", "source_block": "core_blocks"},
                {"name": "small_penalties", "signed_contribution": round(-small_penalties * 0.16, 4), "direction": "negative" if small_penalties > 0 else "neutral", "short_explanation": "Small penalties only address clear overreaction, crowding, or legitimacy breaks.", "source_block": "primary_signals"},
            ],
            "fragility_risk": [{"name": "fragility", "signed_contribution": round((fragility_block - 0.5), 4), "direction": "positive" if fragility_block >= 0.5 else "negative", "short_explanation": "Fragility risk is driven directly by the fragility block.", "source_block": "core_blocks"}],
            "signal_confidence": [
                {"name": "data_confidence", "signed_contribution": round((confidence_components["data_confidence"] - 0.5) * 0.40, 4), "direction": "positive" if confidence_components["data_confidence"] >= 0.5 else "negative", "short_explanation": "Conditioned data quality is the main confidence driver.", "source_block": "base_components"},
                {"name": "market_confidence", "signed_contribution": round((confidence_components["market_confidence"] - 0.5) * 0.30, 4), "direction": "positive" if confidence_components["market_confidence"] >= 0.5 else "negative", "short_explanation": "Market structure contributes to confidence when the thesis is executable.", "source_block": "base_components"},
                {"name": "thesis_confidence", "signed_contribution": round((confidence_components["thesis_confidence"] - 0.5) * 0.30, 4), "direction": "positive" if confidence_components["thesis_confidence"] >= 0.5 else "negative", "short_explanation": "The thesis remains stronger when evidence is coherent and not overly reflexive.", "source_block": "base_components"},
            ],
        }
        # Keep only the compact public compatibility surface that is still
        # useful outside the V2 bundle structure.
        compatibility_raw = {
            "fundamental_health": fundamental_health,
            "opportunity_underreaction": opportunity_underreaction,
            "fragility_block": fragility_block,
            "evidence_confidence": evidence_confidence,
            "data_confidence": confidence_components["data_confidence"],
            "market_confidence": confidence_components["market_confidence"],
            "thesis_confidence": confidence_components["thesis_confidence"],
            "market_legitimacy": market_legitimacy,
        }
        bundle.raw.update(compatibility_raw)
        primary = PrimarySignals(
            fundamental_quality=fundamental_quality,
            mispricing_signal=mispricing_signal,
            fragility_risk=fragility_block,
            signal_confidence=signal_confidence,
        )
        bundle.primary_signals = primary
        bundle.axes = _legacy_axes_from_primary(primary, bundle)
    return raw_bundles
