from dataclasses import dataclass

from collectors.models import HistoricalFeaturePoint, RawSubnetSnapshot
from explain.engine import build_explanation
from features.metrics import compute_raw_features, normalize_features
from features.types import AxisScores, FeatureBundle, PrimarySignals
from labels.engine import assign_label
from regimes.hard_rules import HardRuleResult, apply_rule_caps, evaluate_hard_rules
from stress.scenarios import run_stress_tests


@dataclass
class ScoreArtifacts:
    score: float
    primary: PrimarySignals
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
                point.fundamental_quality,
                point.mispricing_signal,
                point.fragility_risk,
                point.signal_confidence,
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
            history_point.fundamental_quality,
            history_point.signal_confidence,
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


def _signals_from_legacy_history(point: HistoricalFeaturePoint) -> PrimarySignals:
    fundamental = max(
        0.0,
        min(
            1.0,
            0.55 * (point.intrinsic_quality or 0.0)
            + 0.25 * (point.economic_sustainability or 0.0)
            + 0.20 * max(0.0, 1.0 - (point.reflexivity or 0.0)),
        ),
    )
    mispricing = max(0.0, min(1.0, 0.5 + (point.opportunity_gap or 0.0) / 2.0))
    fragility = max(
        0.0,
        min(
            1.0,
            0.55 * max(0.0, 1.0 - (point.stress_robustness or 0.0))
            + 0.45 * (point.reflexivity or 0.0),
        ),
    )
    confidence = max(0.0, min(1.0, 0.45 + 0.35 * (point.stress_robustness or 0.0)))
    return PrimarySignals(
        fundamental_quality=fundamental,
        mispricing_signal=mispricing,
        fragility_risk=fragility,
        signal_confidence=confidence,
    )


def _history_fallback_primary(snapshot: RawSubnetSnapshot, current_primary: PrimarySignals) -> PrimarySignals:
    history_point = _latest_valid_history_point(snapshot)
    if history_point is None:
        return current_primary

    history_primary = (
        PrimarySignals(
            fundamental_quality=history_point.fundamental_quality,
            mispricing_signal=history_point.mispricing_signal,
            fragility_risk=history_point.fragility_risk,
            signal_confidence=history_point.signal_confidence,
        )
        if all(
            value is not None
            for value in (
                history_point.fundamental_quality,
                history_point.mispricing_signal,
                history_point.fragility_risk,
                history_point.signal_confidence,
            )
        )
        else _signals_from_legacy_history(history_point)
    )

    def _blend(history_value: float, current_value: float, history_weight: float = 0.9) -> float:
        return max(0.0, min(1.0, history_weight * history_value + (1.0 - history_weight) * current_value))

    return PrimarySignals(
        fundamental_quality=_blend(history_primary.fundamental_quality, current_primary.fundamental_quality),
        mispricing_signal=_blend(history_primary.mispricing_signal, current_primary.mispricing_signal),
        fragility_risk=_blend(history_primary.fragility_risk, current_primary.fragility_risk),
        signal_confidence=_blend(history_primary.signal_confidence, current_primary.signal_confidence),
    )


def _limit_signal_drift(current_value: float, history_value: float | None, max_step: float) -> float:
    if history_value is None:
        return current_value
    lower = max(0.0, history_value - max_step)
    upper = min(1.0, history_value + max_step)
    return max(lower, min(upper, current_value))


def _stabilize_primary_with_history(snapshot: RawSubnetSnapshot, current_primary: PrimarySignals) -> PrimarySignals:
    history_point = _latest_valid_history_point(snapshot)
    if history_point is None:
        return current_primary

    history_primary = (
        PrimarySignals(
            fundamental_quality=history_point.fundamental_quality,
            mispricing_signal=history_point.mispricing_signal,
            fragility_risk=history_point.fragility_risk,
            signal_confidence=history_point.signal_confidence,
        )
        if all(
            value is not None
            for value in (
                history_point.fundamental_quality,
                history_point.mispricing_signal,
                history_point.fragility_risk,
                history_point.signal_confidence,
            )
        )
        else _signals_from_legacy_history(history_point)
    )

    return PrimarySignals(
        fundamental_quality=_limit_signal_drift(current_primary.fundamental_quality, history_primary.fundamental_quality, 0.08),
        mispricing_signal=_limit_signal_drift(current_primary.mispricing_signal, history_primary.mispricing_signal, 0.10),
        fragility_risk=_limit_signal_drift(current_primary.fragility_risk, history_primary.fragility_risk, 0.08),
        signal_confidence=_limit_signal_drift(current_primary.signal_confidence, history_primary.signal_confidence, 0.08),
    )


def _legacy_axes_from_primary(signals: PrimarySignals, bundle: FeatureBundle, stress_robustness: float | None = None) -> AxisScores:
    intrinsic = max(0.0, min(1.0, 0.82 * signals.fundamental_quality + 0.18 * (bundle.raw.get("cohort_quality_edge") or 0.0)))
    economic = max(
        0.0,
        min(
            1.0,
            0.45 * signals.fundamental_quality
            + 0.35 * (1.0 - signals.fragility_risk)
            + 0.20 * max(0.0, signals.signal_confidence - 0.10),
        ),
    )
    reflexivity = max(
        0.0,
        min(
            1.0,
            0.55 * signals.fragility_risk
            + 0.30 * (bundle.raw.get("crowding_proxy") or 0.0)
            + 0.15 * max(0.0, 1.0 - signals.mispricing_signal),
        ),
    )
    stress_component = 1.0 - signals.fragility_risk if stress_robustness is None else stress_robustness
    opportunity_gap = max(-1.0, min(1.0, (signals.mispricing_signal - 0.5) * 2.0))
    return AxisScores(
        intrinsic_quality=intrinsic,
        economic_sustainability=economic,
        reflexivity=reflexivity,
        stress_robustness=max(0.0, min(1.0, stress_component)),
        opportunity_gap=opportunity_gap,
    )


def _ranking_priority_score(signals: PrimarySignals, bundle: FeatureBundle) -> float:
    market_relevance = bundle.raw.get("market_relevance_proxy") or bundle.raw.get("cohort_relevance_edge") or 0.0
    fragility_headwind = max(0.0, (signals.fragility_risk - 0.55) / 0.45)
    resilience = max(0.0, 1.0 - fragility_headwind)
    return max(
        0.0,
        min(
            1.0,
            0.30 * signals.fundamental_quality
            + 0.32 * signals.mispricing_signal
            + 0.16 * signals.signal_confidence
            + 0.14 * resilience
            + 0.08 * market_relevance,
        ),
    )


def _apply_total_cap(score: float, signals: PrimarySignals | AxisScores, rules: HardRuleResult) -> float:
    if isinstance(signals, AxisScores):
        signals = _signals_from_legacy_history(
            HistoricalFeaturePoint(
                timestamp="",
                intrinsic_quality=signals.intrinsic_quality,
                economic_sustainability=signals.economic_sustainability,
                reflexivity=signals.reflexivity,
                stress_robustness=signals.stress_robustness,
                opportunity_gap=signals.opportunity_gap,
            )
        )
    if rules.legacy_score_cap is None:
        return score
    if not rules.force_negative_label:
        return min(score, rules.legacy_score_cap)

    regime_quality = max(
        0.0,
        min(
            1.0,
            0.45 * signals.fundamental_quality
            + 0.35 * (1.0 - signals.fragility_risk)
            + 0.20 * signals.signal_confidence,
        ),
    )
    shaped_cap = rules.legacy_score_cap * (0.55 + 0.45 * regime_quality)
    return min(score, shaped_cap)


def build_scores(snapshots: list[RawSubnetSnapshot]) -> dict[int, ScoreArtifacts]:
    bundles = normalize_features([compute_raw_features(snapshot) for snapshot in snapshots])
    results: dict[int, ScoreArtifacts] = {}

    for snapshot, bundle in zip(snapshots, bundles):
        provisional_primary = bundle.primary_signals or PrimarySignals(0.0, 0.0, 1.0, 0.0)
        if _is_incomplete_snapshot(snapshot, bundle):
            fallback_primary = _history_fallback_primary(snapshot, provisional_primary)
            fallback_axes = _legacy_axes_from_primary(fallback_primary, bundle)
            stress = run_stress_tests(snapshot, bundle, fallback_axes)
            fallback_primary = PrimarySignals(
                fundamental_quality=fallback_primary.fundamental_quality,
                mispricing_signal=fallback_primary.mispricing_signal,
                fragility_risk=max(fallback_primary.fragility_risk, 1.0 - stress.robustness),
                signal_confidence=max(0.35, fallback_primary.signal_confidence),
            )
            axes = _legacy_axes_from_primary(fallback_primary, bundle, stress.robustness)
            score = _ranking_priority_score(fallback_primary, bundle)
            label = "Under Review"
            thesis = (
                "Latest telemetry is incomplete, so the framework falls back to the subnet's recently validated "
                "investment state instead of mistaking the data gap for structural deterioration."
            )
            rules = HardRuleResult(activated=["telemetry_gap_uses_recent_history"])
            explanation = build_explanation(bundle, fallback_primary, axes, stress, rules, label, thesis)
            results[snapshot.netuid] = ScoreArtifacts(
                score=round(score * 100, 2),
                primary=fallback_primary,
                axes=axes,
                bundle=bundle,
                label=label,
                thesis=thesis,
                explanation=explanation,
            )
            continue

        rules = evaluate_hard_rules(snapshot, bundle)
        primary = apply_rule_caps(provisional_primary, rules)
        provisional_axes = _legacy_axes_from_primary(primary, bundle)
        stress = run_stress_tests(snapshot, bundle, provisional_axes)
        primary = PrimarySignals(
            fundamental_quality=primary.fundamental_quality,
            mispricing_signal=primary.mispricing_signal,
            fragility_risk=max(primary.fragility_risk, 0.65 * primary.fragility_risk + 0.35 * (1.0 - stress.robustness)),
            signal_confidence=primary.signal_confidence,
        )
        primary = _stabilize_primary_with_history(snapshot, primary)
        axes = _legacy_axes_from_primary(primary, bundle, stress.robustness)
        score = _apply_total_cap(_ranking_priority_score(primary, bundle), primary, rules)
        label, thesis = assign_label(primary, bundle, stress, rules)
        explanation = build_explanation(bundle, primary, axes, stress, rules, label, thesis)
        results[snapshot.netuid] = ScoreArtifacts(
            score=round(score * 100, 2),
            primary=primary,
            axes=axes,
            bundle=bundle,
            label=label,
            thesis=thesis,
            explanation=explanation,
        )
    return results
