from collectors.models import HistoricalFeaturePoint, RawSubnetSnapshot
from explain.engine import build_explanation
from features.metrics import compute_raw_features, normalize_features
from features.types import AxisScores, PrimarySignals
from regimes.hard_rules import HardRuleResult
from stress.scenarios import StressTestResult


def _snapshot(**overrides) -> RawSubnetSnapshot:
    base = RawSubnetSnapshot(
        netuid=42,
        current_block=1000,
        n_total=12,
        yuma_neurons=12,
        active_neurons_7d=6,
        total_stake_tao=10_000.0,
        unique_coldkeys=6,
        top3_stake_fraction=0.45,
        emission_per_block_tao=0.04,
        incentive_scores=[0.4, 0.35, 0.25],
        n_validators=6,
        tao_in_pool=20_000.0,
        alpha_in_pool=2_000.0,
        alpha_price_tao=10.0,
        coldkey_stakes=[3000.0, 2500.0, 2000.0, 1500.0, 1000.0],
        validator_stakes=[2200.0, 1800.0, 1700.0, 1600.0, 1400.0, 1300.0],
        validator_weight_matrix=[],
        validator_bond_matrix=[],
        last_update_blocks=[1000] * 12,
        yuma_mask=[True] * 12,
        mechanism_ids=[0] * 12,
        immunity_period=14,
        registration_allowed=True,
        target_regs_per_interval=1,
        min_burn=0.0,
        max_burn=0.0,
        difficulty=0.0,
        history=[
            HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=9.8, tao_in_pool=18_000.0, active_ratio=0.45, fundamental_quality=0.48),
            HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=9.9, tao_in_pool=18_800.0, active_ratio=0.49, fundamental_quality=0.52),
            HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=10.0, tao_in_pool=19_400.0, active_ratio=0.53, fundamental_quality=0.56),
        ],
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_conditioning_marks_bounded_and_reconstructed_inputs():
    bundle = compute_raw_features(
        _snapshot(
            tao_in_pool=-10.0,
            alpha_in_pool=50.0,
            alpha_price_tao=0.0,
            top3_stake_fraction=1.8,
            validator_stakes=[10.0, -5.0, 7.0],
        )
    )

    assert "tao_in_pool" in bundle.conditioned.visibility["bounded"]
    assert "top3_stake_fraction" in bundle.conditioned.visibility["bounded"]
    assert bundle.raw["reserve_depth"] == 0.0
    assert bundle.conditioned.reliability["market_data_reliability"] >= 0.0


def test_monotonic_liquidity_health_supports_mispricing_when_other_inputs_hold():
    low_liquidity, high_liquidity = normalize_features(
        [
            compute_raw_features(_snapshot(tao_in_pool=4_000.0, alpha_in_pool=120.0)),
            compute_raw_features(_snapshot(tao_in_pool=40_000.0, alpha_in_pool=8_000.0)),
        ]
    )

    assert low_liquidity.base_components["liquidity_health"] < high_liquidity.base_components["liquidity_health"]
    assert low_liquidity.primary_signals.mispricing_signal <= high_liquidity.primary_signals.mispricing_signal


def test_explainability_uses_block_and_primary_contributors():
    bundle = normalize_features([compute_raw_features(_snapshot())])[0]
    stress = StressTestResult(scenarios=[], robustness=0.8, fragility_class="robust", max_drawdown=0.12)
    explanation = build_explanation(
        bundle,
        bundle.primary_signals or PrimarySignals(0.0, 0.0, 1.0, 0.0),
        bundle.axes or AxisScores(0.0, 0.0, 0.0, 0.0, 0.0),
        stress,
        HardRuleResult(activated=[]),
        "Under Review",
        "Synthetic test thesis",
    )

    assert explanation["block_scores"]["fundamental_health"] >= 0.0
    assert explanation["primary_signal_contributors"]["mispricing_signal"]
    assert all(item["signed_contribution"] <= 0 for item in explanation["top_negative_drags"])
    assert "visibility" in explanation["conditioning"]


def test_missing_history_reduces_history_reliability_and_signal_confidence():
    rich_bundle, thin_bundle = normalize_features(
        [
            compute_raw_features(_snapshot()),
            compute_raw_features(_snapshot(history=[])),
        ]
    )

    assert rich_bundle.raw["history_data_reliability"] > thin_bundle.raw["history_data_reliability"]
    assert rich_bundle.raw["history_depth_score"] > thin_bundle.raw["history_depth_score"]
    assert rich_bundle.raw["data_confidence"] >= thin_bundle.raw["data_confidence"]
    assert rich_bundle.raw["history_signal_coverage"] > thin_bundle.raw["history_signal_coverage"]


def test_missing_validator_signals_are_visible_in_conditioning_and_confidence():
    with_validator_data, without_validator_data = normalize_features(
        [
            compute_raw_features(
                _snapshot(
                    validator_weight_matrix=[[0.4, 0.3, 0.2, 0.1], [0.3, 0.3, 0.2, 0.2]],
                    validator_bond_matrix=[[0.5, 0.3, 0.2], [0.45, 0.35, 0.2]],
                )
            ),
            compute_raw_features(_snapshot(validator_weight_matrix=[], validator_bond_matrix=[])),
        ]
    )

    assert with_validator_data.raw["validator_data_reliability"] > without_validator_data.raw["validator_data_reliability"]
    assert with_validator_data.raw["market_confidence"] >= without_validator_data.raw["market_confidence"]


def test_higher_concentration_does_not_reduce_fragility():
    balanced, concentrated = normalize_features(
        [
            compute_raw_features(_snapshot(top3_stake_fraction=0.35, incentive_scores=[0.35, 0.33, 0.32])),
            compute_raw_features(_snapshot(top3_stake_fraction=0.82, incentive_scores=[0.9, 0.07, 0.03])),
        ]
    )

    assert balanced.raw["concentration"] < concentrated.raw["concentration"]
    assert balanced.primary_signals.fragility_risk <= concentrated.primary_signals.fragility_risk


def test_small_input_changes_do_not_create_large_score_jumps():
    base, tweaked = normalize_features(
        [
            compute_raw_features(_snapshot(tao_in_pool=20_000.0, alpha_in_pool=2_000.0, active_neurons_7d=6)),
            compute_raw_features(_snapshot(tao_in_pool=20_800.0, alpha_in_pool=2_050.0, active_neurons_7d=6)),
        ]
    )

    assert abs(base.primary_signals.fundamental_quality - tweaked.primary_signals.fundamental_quality) < 0.12
    assert abs(base.primary_signals.mispricing_signal - tweaked.primary_signals.mispricing_signal) < 0.30
    assert abs(base.primary_signals.fragility_risk - tweaked.primary_signals.fragility_risk) < 0.20
    assert abs(base.primary_signals.signal_confidence - tweaked.primary_signals.signal_confidence) < 0.12
