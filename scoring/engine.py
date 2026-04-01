from dataclasses import dataclass

from collectors.models import HistoricalFeaturePoint, RawSubnetSnapshot
from explain.engine import build_explanation
from features.metrics import compute_raw_features, normalize_features
from features.types import AxisScores, FeatureBundle, PrimarySignals
from labels.engine import assign_label
from regimes.hard_rules import HardRuleResult, apply_rule_caps, evaluate_hard_rules
from stress.scenarios import run_stress_tests

PRIMARY_SIGNAL_DRIFT_CAPS = {
    "fundamental_quality": 0.08,
    "mispricing_signal": 0.10,
    "fragility_risk": 0.08,
    "signal_confidence": 0.08,
}

RANKING_DRIFT_CAP = 0.035
RANKING_HISTORY_BLEND = 0.70


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


def _history_primary_signals(point: HistoricalFeaturePoint) -> PrimarySignals:
    if all(
        value is not None
        for value in (
            point.fundamental_quality,
            point.mispricing_signal,
            point.fragility_risk,
            point.signal_confidence,
        )
    ):
        return PrimarySignals(
            fundamental_quality=point.fundamental_quality,
            mispricing_signal=point.mispricing_signal,
            fragility_risk=point.fragility_risk,
            signal_confidence=point.signal_confidence,
        )
    return _signals_from_legacy_history(point)


def _history_fallback_primary(snapshot: RawSubnetSnapshot, current_primary: PrimarySignals) -> PrimarySignals:
    history_point = _latest_valid_history_point(snapshot)
    if history_point is None:
        return current_primary

    history_primary = _history_primary_signals(history_point)

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

    history_primary = _history_primary_signals(history_point)

    return PrimarySignals(
        fundamental_quality=_limit_signal_drift(current_primary.fundamental_quality, history_primary.fundamental_quality, PRIMARY_SIGNAL_DRIFT_CAPS["fundamental_quality"]),
        mispricing_signal=_limit_signal_drift(current_primary.mispricing_signal, history_primary.mispricing_signal, PRIMARY_SIGNAL_DRIFT_CAPS["mispricing_signal"]),
        fragility_risk=_limit_signal_drift(current_primary.fragility_risk, history_primary.fragility_risk, PRIMARY_SIGNAL_DRIFT_CAPS["fragility_risk"]),
        signal_confidence=_limit_signal_drift(current_primary.signal_confidence, history_primary.signal_confidence, PRIMARY_SIGNAL_DRIFT_CAPS["signal_confidence"]),
    )


def _legacy_axes_from_primary(signals: PrimarySignals, bundle: FeatureBundle, stress_robustness: float | None = None) -> AxisScores:
    # AxisScores remain a compatibility projection for labels, stress, and
    # persisted surfaces that still expect the older axis vocabulary.
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
    ranking_artifacts = bundle.ranking or {}
    market_relevance = ranking_artifacts.get("market_relevance")
    if market_relevance is None:
        market_relevance = (
            bundle.core_blocks.get("market_legitimacy")
            or bundle.base_components.get("market_relevance")
            or bundle.raw.get("market_legitimacy")
            or bundle.raw.get("market_relevance_proxy")
            or bundle.raw.get("cohort_relevance_edge")
            or 0.0
        )
    thesis_strength = ranking_artifacts.get("thesis_strength")
    base_opportunity = bundle.core_blocks.get("opportunity_underreaction")
    if base_opportunity is None:
        base_opportunity = bundle.base_components.get("opportunity_underreaction")
    fragility_headwind = max(0.0, (signals.fragility_risk - 0.55) / 0.45)
    resilience = ranking_artifacts.get("resilience")
    if resilience is None:
        resilience = 1.0 - (bundle.core_blocks.get("fragility") or signals.fragility_risk)
        resilience = max(0.0, min(1.0, resilience))
    mispricing_component = base_opportunity if base_opportunity is not None else signals.mispricing_signal
    thesis_component = thesis_strength if thesis_strength is not None else (
        0.45 * signals.fundamental_quality
        + 0.35 * mispricing_component
        + 0.20 * signals.signal_confidence
    )
    return max(
        0.0,
        min(
            1.0,
            0.24 * signals.fundamental_quality
            + 0.24 * mispricing_component
            + 0.20 * thesis_component
            + 0.14 * signals.signal_confidence
            + 0.10 * resilience
            + 0.08 * market_relevance,
        ),
    )


def _history_priority_score(snapshot: RawSubnetSnapshot, bundle: FeatureBundle) -> float | None:
    history_point = _latest_valid_history_point(snapshot)
    if history_point is None:
        return None

    history_primary = _history_primary_signals(history_point)
    return _ranking_priority_score(history_primary, bundle)


def _stabilize_priority_with_history(snapshot: RawSubnetSnapshot, bundle: FeatureBundle, current_score: float) -> float:
    history_score = _history_priority_score(snapshot, bundle)
    if history_score is None:
        return current_score

    # Damp tiny run-to-run movements at the actual ranking layer so adjacent
    # names with near-identical scores do not keep leapfrogging every few minutes.
    blended_score = RANKING_HISTORY_BLEND * history_score + (1.0 - RANKING_HISTORY_BLEND) * current_score
    return _limit_signal_drift(blended_score, history_score, RANKING_DRIFT_CAP)


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
            # Telemetry-gap handling is the one place where history stays in the
            # critical path: we preserve the latest validated V2 state, then run
            # the normal V2 ranking and stress layers on top of it.
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
            score = _stabilize_priority_with_history(snapshot, bundle, _ranking_priority_score(fallback_primary, bundle))
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
        # Stress and labels still consume AxisScores, but the primary runtime
        # truth is the V2 signal vector and V2 ranking artifacts.
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
        score = _stabilize_priority_with_history(snapshot, bundle, _ranking_priority_score(primary, bundle))
        score = _apply_total_cap(score, primary, rules)
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
