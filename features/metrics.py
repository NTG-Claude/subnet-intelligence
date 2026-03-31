import math
from statistics import fmean
from typing import Iterable

from collectors.models import HistoricalFeaturePoint, RawSubnetSnapshot
from features.types import AxisScores, FeatureBundle, FeatureMetric
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
    if anchor == 0:
        return None
    return (current - anchor) / abs(anchor)


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
        if snapshot.validator_weight_matrix else 0.0
    )
    cross_validator_disagreement = mean_pairwise_l1(snapshot.validator_weight_matrix)
    meaningful_discrimination = (
        fmean(1.0 - normalized_entropy(row) for row in snapshot.validator_weight_matrix)
        if snapshot.validator_weight_matrix else 0.0
    )
    bond_responsiveness = (
        fmean(1.0 - normalized_entropy(row) for row in snapshot.validator_bond_matrix)
        if snapshot.validator_bond_matrix else None
    )

    slippage_1 = simulate_tao_buy_slippage(snapshot.tao_in_pool, snapshot.alpha_in_pool, 1.0)
    slippage_10 = simulate_tao_buy_slippage(snapshot.tao_in_pool, snapshot.alpha_in_pool, 10.0)
    slippage_50 = simulate_tao_buy_slippage(snapshot.tao_in_pool, snapshot.alpha_in_pool, 50.0)
    avg_slippage = fmean(v for v in [slippage_1, slippage_10, slippage_50] if v is not None) if any(
        v is not None for v in [slippage_1, slippage_10, slippage_50]
    ) else None

    price_history = _history_values(snapshot.history, "alpha_price_tao")
    quality_history = _history_values(snapshot.history, "intrinsic_quality")
    emission_history = _history_values(snapshot.history, "emission_per_block_tao")
    active_history = _history_values(snapshot.history, "active_ratio")
    flow_history = _history_values(snapshot.history, "tao_in_pool")

    price_change = _change_vs_history(snapshot.alpha_price_tao, price_history)
    quality_change = _change_vs_history(active_ratio, active_history if active_history else quality_history)
    emission_change = _change_vs_history(snapshot.emission_per_block_tao, emission_history)
    reserve_change = _change_vs_history(snapshot.tao_in_pool, flow_history)

    return FeatureBundle(
        raw={
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
            "crowding_proxy": fmean([validator_dominance, incentive_concentration, clamp01(avg_slippage or 0.0)]),
            "sharp_short_term_reversal_risk": max(0.0, (price_change or 0.0) - max(_acceleration(quality_history) or 0.0, 0.0)),
            "performance_driven_by_few_actors": max(validator_dominance, incentive_concentration),
            "registration_openness": 1.0 if snapshot.registration_allowed else 0.0,
            "pow_registration_enabled": 1.0 if snapshot.difficulty > 0 else 0.0,
            "burn_registration_enabled": 1.0 if snapshot.min_burn > 0 or snapshot.max_burn > 0 else 0.0,
            "immunity_period": float(snapshot.immunity_period),
            "dereg_risk_proxy": clamp01(
                0.45 * max(0.0, 0.35 - active_ratio)
                + 0.25 * max(0.0, 0.20 - participation_breadth)
                + 0.20 * max(validator_dominance, incentive_concentration)
                + 0.10 * (1.0 if snapshot.registration_allowed else 0.0)
            ),
            "repo_commits_30d": float(snapshot.github.commits_30d) if snapshot.github else None,
            "repo_contributors_30d": float(snapshot.github.contributors_30d) if snapshot.github else None,
            "repo_recency": None if not snapshot.github or not snapshot.github.last_push else 1.0,
        }
    )


def normalize_features(raw_bundles: list[FeatureBundle]) -> list[FeatureBundle]:
    metric_map = {
        "active_ratio": ("direct_onchain", "intrinsic_quality", 0.14, False),
        "participation_breadth": ("direct_onchain", "intrinsic_quality", 0.10, False),
        "validator_participation": ("direct_onchain", "intrinsic_quality", 0.08, False),
        "incentive_distribution_quality": ("derived_onchain", "intrinsic_quality", 0.10, False),
        "update_freshness": ("direct_onchain", "intrinsic_quality", 0.08, False),
        "validator_weight_entropy": ("derived_onchain", "intrinsic_quality", 0.07, False),
        "cross_validator_disagreement": ("derived_onchain", "intrinsic_quality", 0.13, False),
        "meaningful_discrimination": ("derived_onchain", "intrinsic_quality", 0.12, False),
        "bond_responsiveness": ("derived_onchain", "intrinsic_quality", 0.08, False),
        "incentive_concentration": ("derived_onchain", "intrinsic_quality", 0.10, True),
        "validator_dominance": ("derived_onchain", "intrinsic_quality", 0.10, True),
        "reserve_depth": ("direct_onchain", "economic_sustainability", 0.18, False),
        "alpha_reserve": ("direct_onchain", "economic_sustainability", 0.08, False),
        "tao_reserve": ("direct_onchain", "economic_sustainability", 0.08, False),
        "slippage_1_tao": ("simulated", "economic_sustainability", 0.06, True),
        "slippage_10_tao": ("simulated", "economic_sustainability", 0.10, True),
        "slippage_50_tao": ("simulated", "economic_sustainability", 0.16, True),
        "liquidity_thinness": ("simulated", "economic_sustainability", 0.14, True),
        "emission_efficiency": ("derived_onchain", "economic_sustainability", 0.12, False),
        "emission_concentration": ("derived_onchain", "economic_sustainability", 0.08, True),
        "emission_persistence": ("needs_history", "economic_sustainability", 0.08, False),
        "flow_stability": ("needs_history", "economic_sustainability", 0.10, False),
        "flow_to_price_elasticity": ("needs_history", "reflexivity", 0.16, True),
        "price_move_without_quality_improvement": ("needs_history", "reflexivity", 0.20, True),
        "emission_spike_without_participation_improvement": ("needs_history", "reflexivity", 0.16, True),
        "reserve_sensitivity": ("simulated", "reflexivity", 0.12, True),
        "crowding_proxy": ("derived_onchain", "reflexivity", 0.18, True),
        "sharp_short_term_reversal_risk": ("needs_history", "reflexivity", 0.10, True),
        "performance_driven_by_few_actors": ("derived_onchain", "reflexivity", 0.08, True),
        "repo_commits_30d": ("derived_onchain", "intrinsic_quality", 0.02, False),
        "repo_contributors_30d": ("derived_onchain", "intrinsic_quality", 0.02, False),
        "repo_recency": ("derived_onchain", "intrinsic_quality", 0.00, False),
    }
    all_values = {key: [bundle.raw.get(key) for bundle in raw_bundles] for key in metric_map}

    for bundle in raw_bundles:
        metrics: dict[str, FeatureMetric] = {}
        for key, (category, axis, weight, inverse) in metric_map.items():
            value = bundle.raw.get(key)
            if key in {
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
                "repo_recency",
            }:
                normalized = clamp01(value or 0.0)
            else:
                normalized = percentile_rank(value, all_values[key])
            metrics[key] = FeatureMetric(
                name=key,
                value=value,
                normalized=normalized,
                category=category,
                axis=axis,
                weight=weight,
                higher_is_better=not inverse,
            )
        bundle.metrics = metrics
        bundle.axes = compute_axis_scores(bundle)
    return raw_bundles


def _weighted_axis(bundle: FeatureBundle, axis: str) -> float:
    selected = [metric for metric in bundle.metrics.values() if metric.axis == axis and metric.weight > 0]
    if not selected:
        return 0.0
    total_weight = sum(metric.weight for metric in selected)
    total = 0.0
    for metric in selected:
        value = metric.normalized if metric.higher_is_better else (1.0 - metric.normalized)
        total += value * metric.weight
    return total / total_weight


def compute_axis_scores(bundle: FeatureBundle) -> AxisScores:
    return AxisScores(
        intrinsic_quality=clamp01(_weighted_axis(bundle, "intrinsic_quality")),
        economic_sustainability=clamp01(_weighted_axis(bundle, "economic_sustainability")),
        reflexivity=clamp01(_weighted_axis(bundle, "reflexivity")),
        stress_robustness=0.0,
        opportunity_gap=0.0,
    )
