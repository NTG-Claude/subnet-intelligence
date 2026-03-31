from dataclasses import dataclass

from collectors.models import HistoricalFeaturePoint
from collectors.models import RawSubnetSnapshot
from explain.engine import build_explanation
from features.metrics import compute_raw_features, normalize_features
from features.types import AxisScores, FeatureBundle
from labels.engine import assign_label
from regimes.hard_rules import HardRuleResult, apply_rule_caps, evaluate_hard_rules
from stress.scenarios import run_stress_tests


@dataclass
class ScoreArtifacts:
    score: float
    axes: AxisScores
    bundle: FeatureBundle
    label: str
    thesis: str
    explanation: dict


def _latest_valid_history_point(snapshot: RawSubnetSnapshot) -> HistoricalFeaturePoint | None:
    for point in reversed(snapshot.history):
        if any(
            value is not None
            for value in (
                point.intrinsic_quality,
                point.economic_sustainability,
                point.reflexivity,
                point.stress_robustness,
                point.opportunity_gap,
            )
        ):
            return point
    return None


def _is_incomplete_snapshot(snapshot: RawSubnetSnapshot, bundle: FeatureBundle) -> bool:
    history_point = _latest_valid_history_point(snapshot)
    if history_point is None:
        return False

    current_blank = all(
        (bundle.raw.get(key) or 0.0) <= 0.0
        for key in (
            "active_ratio",
            "participation_breadth",
            "validator_participation",
            "reserve_depth",
            "alpha_reserve",
            "tao_reserve",
        )
    )
    history_was_live = (history_point.tao_in_pool or 0.0) > 1000 or any(
        (value or 0.0) > 0.25
        for value in (
            history_point.intrinsic_quality,
            history_point.economic_sustainability,
            history_point.stress_robustness,
        )
    )
    missing_live_market = (
        (snapshot.tao_in_pool or 0.0) <= 0.0
        and (snapshot.alpha_in_pool or 0.0) <= 0.0
        and (snapshot.alpha_price_tao or 0.0) <= 0.0
    )
    missing_participation = (
        snapshot.active_neurons_7d <= 0
        and snapshot.unique_coldkeys <= 0
        and snapshot.n_validators <= 0
    )
    return history_was_live and (current_blank or (missing_live_market and missing_participation))


def _history_fallback_axes(snapshot: RawSubnetSnapshot, current_axes: AxisScores) -> AxisScores:
    history_point = _latest_valid_history_point(snapshot)
    if history_point is None:
        return current_axes

    def _blend(history_value: float | None, current_value: float, history_weight: float = 0.9) -> float:
        if history_value is None:
            return current_value
        return max(0.0, min(1.0, history_weight * history_value + (1.0 - history_weight) * current_value))

    def _blend_gap(history_value: float | None, current_value: float, history_weight: float = 0.9) -> float:
        if history_value is None:
            return current_value
        return max(-1.0, min(1.0, history_weight * history_value + (1.0 - history_weight) * current_value))

    return AxisScores(
        intrinsic_quality=_blend(history_point.intrinsic_quality, current_axes.intrinsic_quality),
        economic_sustainability=_blend(history_point.economic_sustainability, current_axes.economic_sustainability),
        reflexivity=_blend(history_point.reflexivity, current_axes.reflexivity),
        stress_robustness=_blend(history_point.stress_robustness, current_axes.stress_robustness),
        opportunity_gap=_blend_gap(history_point.opportunity_gap, current_axes.opportunity_gap),
    )


def _opportunity_gap(axes: AxisScores, bundle: FeatureBundle) -> float:
    crowding = bundle.raw.get("crowding_proxy") or 0.0
    return max(-1.0, min(1.0, axes.intrinsic_quality + axes.stress_robustness - axes.reflexivity - 0.5 * crowding))


def _total_score(axes: AxisScores) -> float:
    opportunity_norm = max(0.0, min(1.0, 0.5 + axes.opportunity_gap / 2.0))
    return max(
        0.0,
        min(
            1.0,
            0.30 * axes.intrinsic_quality
            + 0.25 * axes.economic_sustainability
            + 0.20 * (1.0 - axes.reflexivity)
            + 0.15 * axes.stress_robustness
            + 0.10 * opportunity_norm,
        ),
    )


def _apply_total_cap(score: float, axes: AxisScores, rules) -> float:
    if rules.total_cap is None:
        return score
    if not rules.force_negative_label:
        return min(score, rules.total_cap)

    # Preserve some differentiation among capped negative regimes instead of
    # flattening most of the universe onto the exact same ceiling.
    regime_quality = max(
        0.0,
        min(
            1.0,
            0.45 * axes.intrinsic_quality
            + 0.35 * axes.stress_robustness
            + 0.20 * (1.0 - axes.reflexivity),
        ),
    )
    shaped_cap = rules.total_cap * (0.55 + 0.45 * regime_quality)
    return min(score, shaped_cap)


def build_scores(snapshots: list[RawSubnetSnapshot]) -> dict[int, ScoreArtifacts]:
    bundles = normalize_features([compute_raw_features(snapshot) for snapshot in snapshots])
    results: dict[int, ScoreArtifacts] = {}
    for snapshot, bundle in zip(snapshots, bundles):
        if _is_incomplete_snapshot(snapshot, bundle):
            fallback_axes = _history_fallback_axes(
                snapshot,
                bundle.axes or AxisScores(0.0, 0.0, 1.0, 0.0, 0.0),
            )
            score = _total_score(fallback_axes)
            label = "Under Review"
            thesis = (
                "Latest telemetry for this subnet is incomplete, so the score falls back to its recent validated state "
                "instead of treating the gap as real structural weakness."
            )
            stress = run_stress_tests(snapshot, bundle, fallback_axes)
            rules = HardRuleResult(activated=["telemetry_gap_uses_recent_history"])
            explanation = build_explanation(bundle, fallback_axes, stress, rules, label, thesis)
            results[snapshot.netuid] = ScoreArtifacts(
                score=round(score * 100, 2),
                axes=fallback_axes,
                bundle=bundle,
                label=label,
                thesis=thesis,
                explanation=explanation,
            )
            continue

        rules = evaluate_hard_rules(snapshot, bundle)
        provisional = bundle.axes or AxisScores(0.0, 0.0, 1.0, 0.0, 0.0)
        capped = apply_rule_caps(provisional, rules)
        stress = run_stress_tests(snapshot, bundle, capped)
        axes = AxisScores(
            intrinsic_quality=capped.intrinsic_quality,
            economic_sustainability=capped.economic_sustainability,
            reflexivity=capped.reflexivity,
            stress_robustness=stress.robustness,
            opportunity_gap=0.0,
        )
        axes.opportunity_gap = _opportunity_gap(axes, bundle)
        score = _total_score(axes)
        score = _apply_total_cap(score, axes, rules)
        label, thesis = assign_label(axes, bundle, stress, rules)
        explanation = build_explanation(bundle, axes, stress, rules, label, thesis)
        results[snapshot.netuid] = ScoreArtifacts(
            score=round(score * 100, 2),
            axes=axes,
            bundle=bundle,
            label=label,
            thesis=thesis,
            explanation=explanation,
        )
    return results
