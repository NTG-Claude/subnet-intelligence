from features.types import AxisScores, FeatureBundle, PrimarySignals
from regimes.hard_rules import HardRuleResult
from stress.scenarios import StressTestResult


def _bundle_score(bundle: FeatureBundle, key: str, fallback: float = 0.0) -> float:
    if key in bundle.core_blocks:
        return float(bundle.core_blocks.get(key, fallback))
    if key in bundle.base_components:
        return float(bundle.base_components.get(key, fallback))
    value = bundle.raw.get(key)
    return fallback if value is None else float(value)


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


def _to_desirability_contribution(item: dict, invert: bool = False) -> dict:
    signed = float(item.get("signed_contribution", 0.0))
    if invert:
        signed = -signed
    direction = "positive" if signed > 0 else "negative" if signed < 0 else "neutral"
    normalized = dict(item)
    normalized["signed_contribution"] = round(signed, 4)
    normalized["direction"] = direction
    return normalized


def _sorted_primary_contributions(bundle: FeatureBundle, signal_name: str, invert: bool = False) -> list[dict]:
    return sorted(
        [_to_desirability_contribution(item, invert=invert) for item in bundle.contributions.get(signal_name, [])],
        key=lambda item: abs(item.get("signed_contribution", 0.0)),
        reverse=True,
    )


def _driver_to_desirability(item: dict, positive: bool) -> dict:
    signed = abs(float(item.get("effect", 0.0)))
    if not positive:
        signed = -signed
    return {
        "name": item.get("metric"),
        "signed_contribution": round(signed, 4),
        "direction": "positive" if positive else "negative",
        "short_explanation": f"{item.get('metric')} acts as a {'support' if positive else 'headwind'} in the current signal mix.",
        "source_block": item.get("category") or "metrics",
    }


def _conditioning_uncertainties(bundle: FeatureBundle) -> list[dict]:
    conditioned = bundle.conditioned
    if conditioned is None:
        return []
    reliability_specs = {
        "market_data_reliability": (
            "market_data_reliability",
            "Conditioned market telemetry is thin, stale, or heavily repaired.",
            "conditioning",
        ),
        "validator_data_reliability": (
            "validator_data_reliability",
            "Validator-side evidence is too sparse to fully trust consensus structure.",
            "conditioning",
        ),
        "history_data_reliability": (
            "history_data_reliability",
            "Historical depth is too limited for a stable before-versus-now read.",
            "conditioning",
        ),
        "external_data_reliability": (
            "external_data_reliability",
            "External corroboration remains light, so the thesis relies mostly on onchain evidence.",
            "conditioning",
        ),
    }
    uncertainties: list[dict] = []
    for key, (name, explanation, source_block) in reliability_specs.items():
        value = conditioned.reliability.get(key, 0.0)
        if value < 0.55:
            uncertainties.append(
                {
                    "name": name,
                    "signed_contribution": round(value - 0.5, 4),
                    "direction": "negative",
                    "short_explanation": explanation,
                    "source_block": source_block,
                }
            )
    reconstructed = conditioned.visibility.get("reconstructed", [])
    if reconstructed:
        ratio = len(reconstructed) / max(len(conditioned.values), 1)
        uncertainties.append(
            {
                "name": "reconstructed_inputs",
                "signed_contribution": round(-ratio, 4),
                "direction": "negative",
                "short_explanation": "Some inputs were reconstructed during conditioning, which lowers conviction in the final mix.",
                "source_block": "conditioning",
            }
        )
    discarded = conditioned.visibility.get("discarded", [])
    if discarded:
        ratio = len(discarded) / max(len(conditioned.values), 1)
        uncertainties.append(
            {
                "name": "discarded_inputs",
                "signed_contribution": round(-ratio, 4),
                "direction": "negative",
                "short_explanation": "Some unusable inputs were discarded during conditioning, so visibility is incomplete.",
                "source_block": "conditioning",
            }
        )
    return uncertainties


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

    primary_contributors = {
        key: sorted(
            bundle.contributions.get(key, []),
            key=lambda item: abs(item.get("signed_contribution", 0.0)),
            reverse=True,
        )
        for key in ("fundamental_quality", "mispricing_signal", "fragility_risk", "signal_confidence")
    }
    block_scores = {
        name: round(score * 100, 2)
        for name, score in bundle.core_blocks.items()
    }
    v2_desirability = (
        _sorted_primary_contributions(bundle, "fundamental_quality")
        + _sorted_primary_contributions(bundle, "mispricing_signal")
        + _sorted_primary_contributions(bundle, "signal_confidence")
        + _sorted_primary_contributions(bundle, "fragility_risk", invert=True)
    )
    top_positive_drivers = [
        item for item in sorted(v2_desirability, key=lambda entry: entry.get("signed_contribution", 0.0), reverse=True)
        if item.get("signed_contribution", 0.0) > 0
    ][:5]
    top_negative_drags = [
        item for item in sorted(v2_desirability, key=lambda entry: entry.get("signed_contribution", 0.0))
        if item.get("signed_contribution", 0.0) < 0
    ][:5]
    if not top_negative_drags:
        fallback_negatives = (
            [_driver_to_desirability(item, positive=False) for item in mispricing_headwinds]
            + [_driver_to_desirability(item, positive=False) for item in quality_headwinds]
            + [_driver_to_desirability(item, positive=False) for item in fragility_drivers]
            + [_driver_to_desirability(item, positive=False) for item in confidence_headwinds]
        )
        seen_negative_names: set[str] = set()
        for item in fallback_negatives:
            name = str(item.get("name") or "")
            if not name or name in seen_negative_names:
                continue
            seen_negative_names.add(name)
            top_negative_drags.append(item)
            if len(top_negative_drags) >= 5:
                break
    uncertainties = _conditioning_uncertainties(bundle)
    for item in _sorted_primary_contributions(bundle, "signal_confidence"):
        if item.get("signed_contribution", 0.0) < 0:
            uncertainties.append(item)
    if not uncertainties:
        for item in confidence_headwinds:
            uncertainties.append(
                {
                    "name": item.get("metric"),
                    "signed_contribution": round(-abs(float(item.get("effect", 0.0))), 4),
                    "direction": "negative",
                    "short_explanation": f"{item.get('metric')} weakens confidence in the current read.",
                    "source_block": item.get("category") or "metrics",
                }
            )
    uncertainties = sorted(uncertainties, key=lambda item: item.get("signed_contribution", 0.0))[:5]

    thesis_breakers = []
    if _bundle_score(bundle, "price_lag", bundle.raw.get("price_response_lag_to_quality_shift") or 0.0) < 0.02:
        thesis_breakers.append("Price has already largely caught up to the quality improvement.")
    if signals.fragility_risk > 0.65:
        thesis_breakers.append("Fragility is already high; any outflow shock would likely dominate the upside thesis.")
    if signals.signal_confidence < 0.45:
        thesis_breakers.append("Evidence quality is too weak or stale to rely on the current signal mix.")
    if _bundle_score(bundle, "thesis_confidence", signals.signal_confidence) < 0.45:
        thesis_breakers.append("Market structure and crowding still make the thesis too fragile to treat as high-conviction.")
    if (bundle.raw.get("post_incentive_retention") or 0.0) <= 0.0:
        thesis_breakers.append("Usage is not retaining once incentives normalize, which weakens the structural thesis.")
    if _bundle_score(bundle, "market_structure_floor") < 0.45:
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
        "top_positive_drivers": top_positive_drivers,
        "top_negative_drags": top_negative_drags,
        "top_negative_drivers": top_negative_drags,
        "block_scores": block_scores,
        "primary_signal_contributors": primary_contributors,
        "key_uncertainties": uncertainties,
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
            "evidence_confidence": round(_bundle_score(bundle, "evidence_confidence") * 100, 2),
            "thesis_confidence": round(_bundle_score(bundle, "thesis_confidence") * 100, 2),
            "data_confidence": round(_bundle_score(bundle, "data_confidence") * 100, 2),
            "market_confidence": round(_bundle_score(bundle, "market_confidence") * 100, 2),
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
        "conditioning": {
            "reliability": bundle.conditioned.reliability if bundle.conditioned else {},
            "visibility": bundle.conditioned.visibility if bundle.conditioned else {},
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
