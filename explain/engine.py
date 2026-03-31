from features.types import AxisScores, FeatureBundle
from regimes.hard_rules import HardRuleResult
from stress.scenarios import StressTestResult


def build_explanation(
    bundle: FeatureBundle,
    axes: AxisScores,
    stress: StressTestResult,
    rules: HardRuleResult,
    label: str,
    thesis: str,
) -> dict:
    signed = []
    for metric in bundle.metrics.values():
        centered = metric.normalized - 0.5
        if not metric.higher_is_better:
            centered = -centered
        signed.append((metric.name, centered * metric.weight, metric))
    positives = sorted((item for item in signed if item[1] > 0), key=lambda item: item[1], reverse=True)[:3]
    negatives = sorted((item for item in signed if item[1] < 0), key=lambda item: item[1])[:3]

    def _fmt(items: list[tuple[str, float, object]]) -> list[dict]:
        return [
            {
                "metric": name,
                "effect": round(effect, 4),
                "value": metric.value,
                "normalized": round(metric.normalized, 4),
                "category": metric.category,
            }
            for name, effect, metric in items
        ]

    return {
        "label": label,
        "thesis": thesis,
        "component_scores": {
            "intrinsic_quality": round(axes.intrinsic_quality * 100, 2),
            "economic_sustainability": round(axes.economic_sustainability * 100, 2),
            "reflexivity": round(axes.reflexivity * 100, 2),
            "stress_robustness": round(axes.stress_robustness * 100, 2),
            "opportunity_gap": round(axes.opportunity_gap * 100, 2),
        },
        "top_positive_drivers": _fmt(positives),
        "top_negative_drivers": _fmt(negatives),
        "activated_hard_rules": rules.activated,
        "stress_drawdown": round(stress.max_drawdown * 100, 2),
        "fragility_class": stress.fragility_class,
        "earned_reflexive_fragile": {
            "earned_strength": round(((axes.intrinsic_quality + axes.economic_sustainability + axes.stress_robustness) / 3) * 100, 2),
            "reflexive_strength": round(axes.reflexivity * 100, 2),
            "fragile_strength": round((1.0 - axes.stress_robustness) * 100, 2),
        },
        "debug_metrics": {
            name: {
                "value": metric.value,
                "normalized": round(metric.normalized, 4),
                "axis": metric.axis,
                "weight": metric.weight,
                "higher_is_better": metric.higher_is_better,
                "contribution": round(metric.contribution, 4),
            }
            for name, metric in bundle.metrics.items()
        },
        "stress_scenarios": [
            {
                "name": scenario.name,
                "score_after": round(scenario.score_after * 100, 2),
                "drawdown": round(scenario.drawdown * 100, 2),
            }
            for scenario in stress.scenarios
        ],
    }
