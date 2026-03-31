from dataclasses import dataclass

from collectors.models import RawSubnetSnapshot
from explain.engine import build_explanation
from features.metrics import compute_raw_features, normalize_features
from features.types import AxisScores, FeatureBundle
from labels.engine import assign_label
from regimes.hard_rules import apply_rule_caps, evaluate_hard_rules
from stress.scenarios import run_stress_tests


@dataclass
class ScoreArtifacts:
    score: float
    axes: AxisScores
    bundle: FeatureBundle
    label: str
    thesis: str
    explanation: dict


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
