from collectors.models import HistoricalFeaturePoint, RawSubnetSnapshot
from features.components_confidence import build_confidence_components
from features.components_opportunity import build_opportunity_components
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
        "Evidence Limited",
        "Synthetic test thesis",
    )

    assert explanation["block_scores"]["fundamental_health"] >= 0.0
    assert explanation["primary_signal_contributors"]["mispricing_signal"]
    assert all(item["signed_contribution"] <= 0 for item in explanation["top_negative_drags"])
    assert "visibility" in explanation["conditioning"]


def test_explainability_treats_high_fragility_as_negative_drag():
    bundle = normalize_features([compute_raw_features(_snapshot())])[0]
    bundle.contributions["fragility_risk"] = [
        {
            "name": "fragility",
            "signed_contribution": 0.31,
            "direction": "positive",
            "short_explanation": "Fragility risk is driven directly by the fragility block.",
            "source_block": "core_blocks",
        }
    ]
    bundle.contributions["signal_confidence"] = [
        {
            "name": "thesis_confidence",
            "signed_contribution": -0.08,
            "direction": "negative",
            "short_explanation": "The thesis remains weaker when evidence is incoherent.",
            "source_block": "core_blocks",
        }
    ]
    stress = StressTestResult(scenarios=[], robustness=0.32, fragility_class="fragile", max_drawdown=0.34)
    explanation = build_explanation(
        bundle,
        bundle.primary_signals or PrimarySignals(0.0, 0.0, 1.0, 0.0),
        bundle.axes or AxisScores(0.0, 0.0, 0.0, 0.0, 0.0),
        stress,
        HardRuleResult(activated=[]),
        "Evidence Limited",
        "Synthetic fragile thesis",
    )

    assert any(item["name"] == "fragility" for item in explanation["top_negative_drags"])
    fragility_item = next(item for item in explanation["top_negative_drags"] if item["name"] == "fragility")
    assert fragility_item["signed_contribution"] < 0
    assert fragility_item["direction"] == "negative"


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


def test_validator_dominance_uses_validator_structure_not_coldkey_top3_share():
    balanced_validators = compute_raw_features(
        _snapshot(
            top3_stake_fraction=0.90,
            validator_stakes=[1000.0] * 6,
            incentive_scores=[0.2, 0.18, 0.17, 0.16, 0.15, 0.14],
        )
    )
    concentrated_validators = compute_raw_features(
        _snapshot(
            top3_stake_fraction=0.40,
            validator_stakes=[5000.0, 3000.0, 1200.0, 500.0, 200.0, 100.0],
            incentive_scores=[0.2, 0.18, 0.17, 0.16, 0.15, 0.14],
        )
    )

    assert balanced_validators.raw["validator_dominance"] < 0.10
    assert concentrated_validators.raw["validator_dominance"] > balanced_validators.raw["validator_dominance"]


def test_reconstructed_price_input_is_downweighted_in_mispricing_paths():
    history = [
        HistoricalFeaturePoint(
            timestamp="2026-03-29T00:00:00+00:00",
            alpha_price_tao=7.0,
            tao_in_pool=42_000.0,
            emission_per_block_tao=0.03,
            active_ratio=0.40,
            participation_breadth=0.36,
            validator_participation=0.70,
            incentive_distribution_quality=0.65,
            market_structure_floor=0.64,
            fundamental_quality=0.60,
        ),
        HistoricalFeaturePoint(
            timestamp="2026-03-30T00:00:00+00:00",
            alpha_price_tao=7.1,
            tao_in_pool=45_000.0,
            emission_per_block_tao=0.03,
            active_ratio=0.44,
            participation_breadth=0.40,
            validator_participation=0.73,
            incentive_distribution_quality=0.68,
            market_structure_floor=0.67,
            fundamental_quality=0.64,
        ),
        HistoricalFeaturePoint(
            timestamp="2026-03-31T00:00:00+00:00",
            alpha_price_tao=7.2,
            tao_in_pool=48_000.0,
            emission_per_block_tao=0.029,
            active_ratio=0.48,
            participation_breadth=0.44,
            validator_participation=0.76,
            incentive_distribution_quality=0.71,
            market_structure_floor=0.70,
            fundamental_quality=0.68,
        ),
    ]
    explicit = compute_raw_features(
        _snapshot(
            alpha_price_tao=7.3,
            tao_in_pool=50_000.0,
            alpha_in_pool=7_000.0,
            history=history,
        )
    )
    reconstructed = compute_raw_features(
        _snapshot(
            alpha_price_tao=0.0,
            tao_in_pool=50_000.0,
            alpha_in_pool=7_000.0,
            history=history,
        )
    )

    assert reconstructed.raw["price_input_reconstructed"] == 1.0
    assert reconstructed.raw["price_signal_reliability"] < explicit.raw["price_signal_reliability"]
    assert reconstructed.raw["underreaction_score"] <= explicit.raw["underreaction_score"]
    assert reconstructed.raw["overreaction_score"] <= explicit.raw["overreaction_score"]


def test_fragility_primary_signal_matches_v2_fragility_core_block():
    bundle = normalize_features(
        [
            compute_raw_features(_snapshot(top3_stake_fraction=0.78, incentive_scores=[0.88, 0.08, 0.04]))
        ]
    )[0]

    assert bundle.core_blocks["fragility"] == bundle.primary_signals.fragility_risk


def test_small_input_changes_do_not_create_large_score_jumps():
    base, tweaked = normalize_features(
        [
            compute_raw_features(_snapshot(tao_in_pool=20_000.0, alpha_in_pool=2_000.0, active_neurons_7d=6)),
            compute_raw_features(_snapshot(tao_in_pool=20_800.0, alpha_in_pool=2_050.0, active_neurons_7d=6)),
        ]
    )

    assert abs(base.primary_signals.fundamental_quality - tweaked.primary_signals.fundamental_quality) < 0.12
    assert abs(base.primary_signals.mispricing_signal - tweaked.primary_signals.mispricing_signal) < 0.31
    assert abs(base.primary_signals.fragility_risk - tweaked.primary_signals.fragility_risk) < 0.20
    assert abs(base.primary_signals.signal_confidence - tweaked.primary_signals.signal_confidence) < 0.12


def test_participation_without_crowding_retains_level_support_for_established_subnet():
    history = [
        HistoricalFeaturePoint(
            timestamp="2026-03-28T00:00:00+00:00",
            alpha_price_tao=9.7,
            tao_in_pool=18_900.0,
            active_ratio=0.58,
            participation_breadth=0.50,
            validator_participation=0.72,
            incentive_distribution_quality=0.69,
            market_structure_floor=0.71,
            fundamental_quality=0.64,
        ),
        HistoricalFeaturePoint(
            timestamp="2026-03-29T00:00:00+00:00",
            alpha_price_tao=9.9,
            tao_in_pool=19_200.0,
            active_ratio=0.59,
            participation_breadth=0.50,
            validator_participation=0.73,
            incentive_distribution_quality=0.70,
            market_structure_floor=0.72,
            fundamental_quality=0.65,
        ),
        HistoricalFeaturePoint(
            timestamp="2026-03-30T00:00:00+00:00",
            alpha_price_tao=10.0,
            tao_in_pool=19_350.0,
            active_ratio=0.60,
            participation_breadth=0.51,
            validator_participation=0.73,
            incentive_distribution_quality=0.70,
            market_structure_floor=0.72,
            fundamental_quality=0.66,
        ),
    ]

    bundle = compute_raw_features(
        _snapshot(
            alpha_price_tao=10.05,
            tao_in_pool=19_450.0,
            alpha_in_pool=1_950.0,
            active_neurons_7d=7,
            history=history,
        )
    )

    assert bundle.raw["participation_without_crowding"] > 0.15


def test_low_underreaction_is_softened_before_becoming_base_opportunity_drag():
    components = build_opportunity_components(
        raw={},
        normalized={
            "quality_change": 0.0,
            "quality_acceleration": 0.0,
            "reserve_change": 0.0,
            "reserve_growth_without_price": 0.0,
            "price_response_lag_to_quality_shift": 0.0,
            "expected_price_response_gap": 0.0,
            "participation_without_crowding": 0.18,
            "participation_breadth": 0.52,
            "crowding_proxy": 0.28,
            "active_ratio": 0.70,
            "validator_participation": 0.68,
            "cohort_implied_fair_value_gap": 0.14,
            "underreaction_score": 0.08,
        },
    )

    assert components["raw_opportunity_underreaction"] < 0.5
    assert components["opportunity_underreaction"] > components["raw_opportunity_underreaction"]


def test_fair_value_gap_can_lift_opportunity_when_direct_lag_is_only_modest():
    weaker = build_opportunity_components(
        raw={},
        normalized={
            "quality_change": 0.10,
            "quality_acceleration": 0.12,
            "reserve_change": 0.08,
            "reserve_growth_without_price": 0.10,
            "price_response_lag_to_quality_shift": 0.14,
            "expected_price_response_gap": 0.10,
            "participation_without_crowding": 0.42,
            "participation_breadth": 0.56,
            "crowding_proxy": 0.26,
            "active_ratio": 0.70,
            "validator_participation": 0.72,
            "cohort_implied_fair_value_gap": 0.18,
            "underreaction_score": 0.12,
        },
    )
    stronger = build_opportunity_components(
        raw={},
        normalized={
            "quality_change": 0.10,
            "quality_acceleration": 0.12,
            "reserve_change": 0.08,
            "reserve_growth_without_price": 0.10,
            "price_response_lag_to_quality_shift": 0.14,
            "expected_price_response_gap": 0.10,
            "participation_without_crowding": 0.42,
            "participation_breadth": 0.56,
            "crowding_proxy": 0.26,
            "active_ratio": 0.70,
            "validator_participation": 0.72,
            "cohort_implied_fair_value_gap": 0.72,
            "underreaction_score": 0.12,
        },
    )

    assert stronger["fair_value_gap_light"] > weaker["fair_value_gap_light"]
    assert stronger["raw_opportunity_underreaction"] > weaker["raw_opportunity_underreaction"]
    assert stronger["opportunity_underreaction"] > weaker["opportunity_underreaction"]


def test_external_proxies_remain_secondary_inside_thesis_confidence():
    base_components = {
        "market_relevance": 0.66,
        "liquidity_health": 0.72,
        "concentration_health": 0.68,
    }
    opportunity_components = {
        "uncrowded_participation": 0.64,
        "fair_value_gap_light": 0.58,
    }
    fragility_components = {
        "reversal_risk": 0.32,
    }
    common_normalized = {
        "history_depth_score": 0.62,
        "data_coverage": 0.66,
        "consensus_signal_gap": 0.20,
        "confidence_thesis_coherence": 0.74,
        "signal_fabrication_risk": 0.18,
        "update_freshness": 0.70,
        "market_data_reliability": 0.73,
        "validator_data_reliability": 0.67,
        "history_data_reliability": 0.64,
    }

    weak_external = build_confidence_components(
        raw={},
        normalized={
            **common_normalized,
            "external_data_reliability": 0.0,
            "external_source_legitimacy": 0.0,
            "external_dev_recency": 0.0,
            "external_dev_continuity": 0.0,
        },
        base_components=base_components,
        opportunity_components=opportunity_components,
        fragility_components=fragility_components,
    )
    strong_external = build_confidence_components(
        raw={},
        normalized={
            **common_normalized,
            "external_data_reliability": 1.0,
            "external_source_legitimacy": 1.0,
            "external_dev_recency": 1.0,
            "external_dev_continuity": 1.0,
        },
        base_components=base_components,
        opportunity_components=opportunity_components,
        fragility_components=fragility_components,
    )

    assert strong_external["thesis_confidence"] > weak_external["thesis_confidence"]
    assert strong_external["thesis_confidence"] - weak_external["thesis_confidence"] < 0.18
    assert strong_external["data_confidence"] - weak_external["data_confidence"] < 0.08
