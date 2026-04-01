from features.types import AxisScores, FeatureBundle, PrimarySignals
from regimes.hard_rules import HardRuleResult
from stress.scenarios import StressTestResult


def _sorted_drivers(bundle: FeatureBundle, output: str, positive: bool) -> list[tuple[str, float, object]]:
    scored = []
    for metric in bundle.metrics.values():
        if metric.axis != output:
            continue
        centered = metric.normalized - 0.5
        if not metric.higher_is_better:
            centered = -centered
        effect = centered * metric.weight
        if positive and effect > 0:
            scored.append((metric.name, effect, metric))
        if not positive and effect < 0:
            scored.append((metric.name, effect, metric))
    return sorted(scored, key=lambda item: item[1], reverse=positive)[:4]


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


def build_explanation(
    bundle: FeatureBundle,
    signals: PrimarySignals,
    axes: AxisScores,
    stress: StressTestResult,
    rules: HardRuleResult,
    label: str,
    thesis: str,
) -> dict:
    mispricing_support = _fmt(_sorted_drivers(bundle, "mispricing_signal", positive=True))
    mispricing_headwinds = _fmt(_sorted_drivers(bundle, "mispricing_signal", positive=False))
    fragility_drivers = _fmt(_sorted_drivers(bundle, "fragility_risk", positive=True))
    fragility_offsets = _fmt(_sorted_drivers(bundle, "fragility_risk", positive=False))
    confidence_support = _fmt(_sorted_drivers(bundle, "signal_confidence", positive=True))
    confidence_headwinds = _fmt(_sorted_drivers(bundle, "signal_confidence", positive=False))
    quality_support = _fmt(_sorted_drivers(bundle, "fundamental_quality", positive=True))
    quality_headwinds = _fmt(_sorted_drivers(bundle, "fundamental_quality", positive=False))

    thesis_breakers = []
    if (bundle.raw.get("price_response_lag_to_quality_shift") or 0.0) < 0.02:
        thesis_breakers.append("Price has already largely caught up to the quality improvement.")
    if signals.fragility_risk > 0.65:
        thesis_breakers.append("Fragility is already high; any outflow shock would likely dominate the upside thesis.")
    if signals.signal_confidence < 0.45:
        thesis_breakers.append("Evidence quality is too weak or stale to rely on the current signal mix.")
    if (bundle.raw.get("thesis_confidence") or 0.0) < 0.45:
        thesis_breakers.append("Market structure and crowding still make the thesis too fragile to treat as high-conviction.")
    if (bundle.raw.get("post_incentive_retention") or 0.0) <= 0.0:
        thesis_breakers.append("Usage is not retaining once incentives normalize, which weakens the structural thesis.")
    if (bundle.raw.get("market_structure_floor") or 0.0) < 0.45:
        thesis_breakers.append("Market structure is still too thin for larger capital to enter or exit without dominating the thesis.")

    return {
        "label": label,
        "thesis": thesis,
        "primary_outputs": {
            "fundamental_quality": round(signals.fundamental_quality * 100, 2),
            "mispricing_signal": round(signals.mispricing_signal * 100, 2),
            "fragility_risk": round(signals.fragility_risk * 100, 2),
            "signal_confidence": round(signals.signal_confidence * 100, 2),
        },
        "component_scores": {
            "intrinsic_quality": round(axes.intrinsic_quality * 100, 2),
            "economic_sustainability": round(axes.economic_sustainability * 100, 2),
            "reflexivity": round(axes.reflexivity * 100, 2),
            "stress_robustness": round(axes.stress_robustness * 100, 2),
            "opportunity_gap": round(axes.opportunity_gap * 100, 2),
        },
        "top_positive_drivers": quality_support[:3] + mispricing_support[:2],
        "top_negative_drivers": fragility_drivers[:2] + quality_headwinds[:2],
        "why_mispriced": {
            "supports": mispricing_support,
            "headwinds": mispricing_headwinds,
        },
        "risk_drivers": {
            "fragility": fragility_drivers,
            "offsets": fragility_offsets,
        },
        "confidence_rationale": {
            "supports": confidence_support,
            "headwinds": confidence_headwinds,
            "evidence_confidence": round((bundle.raw.get("evidence_confidence") or 0.0) * 100, 2),
            "thesis_confidence": round((bundle.raw.get("thesis_confidence") or 0.0) * 100, 2),
        },
        "quality_rationale": {
            "supports": quality_support,
            "headwinds": quality_headwinds,
        },
        "thesis_breakers": thesis_breakers,
        "activated_hard_rules": rules.activated,
        "stress_drawdown": round(stress.max_drawdown * 100, 2),
        "fragility_class": stress.fragility_class,
        "earned_reflexive_fragile": {
            "earned_strength": round(signals.fundamental_quality * 100, 2),
            "reflexive_strength": round(axes.reflexivity * 100, 2),
            "fragile_strength": round(signals.fragility_risk * 100, 2),
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
