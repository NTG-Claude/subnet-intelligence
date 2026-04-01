import pytest

from collectors.models import HistoricalFeaturePoint, RawSubnetSnapshot
from features.types import AxisScores
from features.types import FeatureBundle, PrimarySignals
from regimes.hard_rules import HardRuleResult
from scoring.engine import (
    PRIMARY_SIGNAL_DRIFT_CAPS,
    RANKING_DRIFT_CAP,
    RANKING_HISTORY_BLEND,
    _apply_total_cap,
    _ranking_priority_score,
    _stabilize_primary_with_history,
    _stabilize_priority_with_history,
    build_scores,
)


def test_apply_total_cap_keeps_plain_caps_for_non_negative_rules():
    axes = AxisScores(
        intrinsic_quality=0.9,
        economic_sustainability=0.9,
        reflexivity=0.2,
        stress_robustness=0.8,
        opportunity_gap=0.4,
    )
    rules = HardRuleResult(activated=[], total_cap=0.2, force_negative_label=False)
    assert _apply_total_cap(0.6, axes, rules) == 0.2


def test_apply_total_cap_preserves_ordering_for_negative_regimes():
    stronger_axes = AxisScores(
        intrinsic_quality=0.8,
        economic_sustainability=0.4,
        reflexivity=0.2,
        stress_robustness=0.7,
        opportunity_gap=-0.1,
    )
    weaker_axes = AxisScores(
        intrinsic_quality=0.3,
        economic_sustainability=0.2,
        reflexivity=0.8,
        stress_robustness=0.2,
        opportunity_gap=-0.4,
    )
    rules = HardRuleResult(activated=["inactive_subnet_blocks_positive_label"], total_cap=0.2, force_negative_label=True)

    stronger = _apply_total_cap(0.6, stronger_axes, rules)
    weaker = _apply_total_cap(0.6, weaker_axes, rules)

    assert stronger < 0.2
    assert weaker < stronger


def test_incomplete_snapshot_uses_recent_history_instead_of_dereg_penalty():
    snapshot = RawSubnetSnapshot(
        netuid=4,
        current_block=1000,
        n_total=256,
        yuma_neurons=256,
        active_neurons_7d=0,
        total_stake_tao=3_000_000.0,
        unique_coldkeys=0,
        top3_stake_fraction=0.58,
        emission_per_block_tao=0.2,
        incentive_scores=[],
        n_validators=0,
        tao_in_pool=0.0,
        alpha_in_pool=0.0,
        alpha_price_tao=0.0,
        coldkey_stakes=[],
        validator_stakes=[],
        validator_weight_matrix=[],
        validator_bond_matrix=[],
        last_update_blocks=[],
        yuma_mask=[],
        mechanism_ids=[],
        immunity_period=0,
        registration_allowed=False,
        target_regs_per_interval=0,
        min_burn=0.0,
        max_burn=0.0,
        difficulty=0.0,
        history=[
            HistoricalFeaturePoint(
                timestamp="2026-03-31T11:46:31+00:00",
                alpha_price_tao=0.064,
                tao_in_pool=133684.0,
                emission_per_block_tao=0.2,
                active_ratio=0.04,
                intrinsic_quality=0.56,
                economic_sustainability=0.71,
                reflexivity=0.67,
                stress_robustness=0.56,
                opportunity_gap=-0.03,
            )
        ],
    )

    artifacts = build_scores([snapshot])[4]

    assert artifacts.score > 25.0
    assert artifacts.label == "Under Review"
    assert "telemetry_gap_uses_recent_history" in artifacts.explanation["activated_hard_rules"]


def test_ranking_priority_rewards_market_relevance_for_flagship_like_subnets():
    signals = PrimarySignals(
        fundamental_quality=0.50,
        mispricing_signal=0.62,
        fragility_risk=0.60,
        signal_confidence=0.48,
    )
    flagship_bundle = FeatureBundle(raw={"market_relevance_proxy": 0.78})
    micro_bundle = FeatureBundle(raw={"market_relevance_proxy": 0.12})

    assert _ranking_priority_score(signals, flagship_bundle) > _ranking_priority_score(signals, micro_bundle)


def test_stabilize_primary_with_history_limits_run_to_run_jumps():
    snapshot = RawSubnetSnapshot(
        netuid=7,
        current_block=1000,
        history=[
            HistoricalFeaturePoint(
                timestamp="2026-03-31T11:46:31+00:00",
                fundamental_quality=0.50,
                mispricing_signal=0.52,
                fragility_risk=0.48,
                signal_confidence=0.54,
            )
        ],
    )
    current = PrimarySignals(
        fundamental_quality=0.70,
        mispricing_signal=0.70,
        fragility_risk=0.70,
        signal_confidence=0.70,
    )

    stabilized = _stabilize_primary_with_history(snapshot, current)

    assert stabilized.fundamental_quality == pytest.approx(0.50 + PRIMARY_SIGNAL_DRIFT_CAPS["fundamental_quality"])
    assert stabilized.mispricing_signal == pytest.approx(0.52 + PRIMARY_SIGNAL_DRIFT_CAPS["mispricing_signal"])
    assert stabilized.fragility_risk == pytest.approx(0.48 + PRIMARY_SIGNAL_DRIFT_CAPS["fragility_risk"])
    assert stabilized.signal_confidence == pytest.approx(0.54 + PRIMARY_SIGNAL_DRIFT_CAPS["signal_confidence"])


def test_stabilize_priority_with_history_limits_leaderboard_pressure():
    snapshot = RawSubnetSnapshot(
        netuid=9,
        current_block=1000,
        history=[
            HistoricalFeaturePoint(
                timestamp="2026-03-31T11:46:31+00:00",
                fundamental_quality=0.52,
                mispricing_signal=0.50,
                fragility_risk=0.42,
                signal_confidence=0.57,
            )
        ],
    )
    bundle = FeatureBundle(raw={"market_relevance_proxy": 0.42})
    history_priority = _ranking_priority_score(
        PrimarySignals(
            fundamental_quality=0.52,
            mispricing_signal=0.50,
            fragility_risk=0.42,
            signal_confidence=0.57,
        ),
        bundle,
    )
    current_priority = _ranking_priority_score(
        PrimarySignals(
            fundamental_quality=0.60,
            mispricing_signal=0.58,
            fragility_risk=0.36,
            signal_confidence=0.64,
        ),
        bundle,
    )

    stabilized = _stabilize_priority_with_history(snapshot, bundle, current_priority)
    expected_blend = RANKING_HISTORY_BLEND * history_priority + (1.0 - RANKING_HISTORY_BLEND) * current_priority

    assert current_priority > history_priority
    assert stabilized > history_priority
    assert stabilized == pytest.approx(expected_blend)
    assert stabilized < current_priority


def test_ranking_priority_prefers_v2_ranking_artifacts_when_available():
    signals = PrimarySignals(
        fundamental_quality=0.55,
        mispricing_signal=0.55,
        fragility_risk=0.45,
        signal_confidence=0.55,
    )
    low_bundle = FeatureBundle(
        raw={"market_relevance_proxy": 0.1, "confidence_adjusted_thesis_strength": 0.2},
        ranking={"market_relevance": 0.2, "thesis_strength": 0.2, "resilience": 0.2},
    )
    high_bundle = FeatureBundle(
        raw={"market_relevance_proxy": 0.1, "confidence_adjusted_thesis_strength": 0.2},
        ranking={"market_relevance": 0.8, "thesis_strength": 0.8, "resilience": 0.8},
    )

    assert _ranking_priority_score(signals, high_bundle) > _ranking_priority_score(signals, low_bundle)


def test_ranking_priority_drift_cap_is_respected():
    history_score = 0.50
    current_score = 0.90
    snapshot = RawSubnetSnapshot(
        netuid=11,
        current_block=1000,
        history=[
            HistoricalFeaturePoint(
                timestamp="2026-03-31T11:46:31+00:00",
                fundamental_quality=0.50,
                mispricing_signal=0.50,
                fragility_risk=0.50,
                signal_confidence=0.50,
            )
        ],
    )
    bundle = FeatureBundle(ranking={"market_relevance": 0.5, "thesis_strength": 0.5, "resilience": 0.5}, raw={})

    stabilized = _stabilize_priority_with_history(snapshot, bundle, current_score)

    assert stabilized <= history_score + RANKING_DRIFT_CAP
