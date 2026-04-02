import pytest

from collectors.models import RawSubnetSnapshot
from features.types import AxisScores, FeatureBundle, PrimarySignals
from regimes.hard_rules import HardRuleResult
from labels.engine import assign_label
from regimes.hard_rules import apply_rule_caps, evaluate_hard_rules
from stress.scenarios import StressTestResult


def _snapshot(**overrides) -> RawSubnetSnapshot:
    base = RawSubnetSnapshot(
        netuid=1,
        current_block=1000,
        n_total=10,
        yuma_neurons=10,
        active_neurons_7d=1,
        total_stake_tao=1000.0,
        unique_coldkeys=3,
        top3_stake_fraction=0.8,
        emission_per_block_tao=0.5,
        incentive_scores=[0.9, 0.1],
        n_validators=2,
        tao_in_pool=10.0,
        alpha_in_pool=1.0,
        alpha_price_tao=10.0,
        coldkey_stakes=[800.0, 200.0],
        validator_stakes=[800.0, 200.0],
        validator_weight_matrix=[[1.0, 0.0], [1.0, 0.0]],
        validator_bond_matrix=[[1.0, 0.0], [1.0, 0.0]],
        last_update_blocks=[0] * 10,
        yuma_mask=[True] * 10,
        mechanism_ids=[0] * 10,
        immunity_period=0,
        registration_allowed=True,
        target_regs_per_interval=1,
        min_burn=0.0,
        max_burn=0.0,
        difficulty=0.0,
        github=None,
        history=[],
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def _bundle(**raw) -> FeatureBundle:
    defaults = {
        "active_ratio": 0.05,
        "slippage_10_tao": 0.7,
        "slippage_50_tao": 0.9,
        "validator_dominance": 0.8,
        "incentive_concentration": 0.8,
        "validator_weight_entropy": 0.95,
        "cross_validator_disagreement": 0.01,
        "meaningful_discrimination": 0.05,
        "dereg_risk_proxy": 0.9,
    }
    defaults.update(raw)
    return FeatureBundle(raw=defaults)


def _stress(max_drawdown: float, robustness: float = 0.1) -> StressTestResult:
    return StressTestResult(
        scenarios=[],
        robustness=robustness,
        fragility_class="fragile",
        max_drawdown=max_drawdown,
    )


def test_micro_pool_apy_forces_overrewarded_rule():
    snapshot = _snapshot(
        active_neurons_7d=8,
        tao_in_pool=10.0,
        emission_per_block_tao=0.5,
        immunity_period=10,
    )
    bundle = _bundle(
        active_ratio=0.8,
        slippage_10_tao=0.1,
        slippage_50_tao=0.2,
        dereg_risk_proxy=0.1,
        validator_weight_entropy=0.3,
        cross_validator_disagreement=0.2,
        meaningful_discrimination=0.5,
    )
    rules = evaluate_hard_rules(snapshot, bundle)
    assert "micro_pool_apy_caps_total_score" in rules.activated
    assert rules.force_label == "Overrewarded"
    assert rules.total_cap is not None and rules.total_cap <= 0.12


def test_small_pool_high_yield_caps_confidence_even_when_not_micro():
    snapshot = _snapshot(
        active_neurons_7d=8,
        tao_in_pool=5_400.0,
        emission_per_block_tao=0.14,
        immunity_period=10,
    )
    bundle = _bundle(
        active_ratio=0.32,
        participation_breadth=0.22,
        slippage_10_tao=0.03,
        slippage_50_tao=0.09,
        validator_dominance=0.86,
        incentive_concentration=1.0,
        market_structure_floor=0.53,
        validator_weight_entropy=0.42,
        cross_validator_disagreement=0.24,
        meaningful_discrimination=0.38,
        dereg_risk_proxy=0.18,
    )

    rules = evaluate_hard_rules(snapshot, bundle)

    assert "small_pool_yield_intensity_caps_confidence" in rules.activated
    assert rules.confidence_cap is not None and rules.confidence_cap <= 0.46


def test_elevated_yield_small_pool_caps_confidence_before_extreme_apy():
    snapshot = _snapshot(
        active_neurons_7d=7,
        tao_in_pool=2_850.0,
        emission_per_block_tao=0.11,
        immunity_period=10,
    )
    bundle = _bundle(
        active_ratio=0.14,
        participation_breadth=0.14,
        slippage_10_tao=0.03,
        slippage_50_tao=0.08,
        validator_dominance=0.835,
        incentive_concentration=0.84,
        market_structure_floor=0.56,
        validator_weight_entropy=0.48,
        cross_validator_disagreement=0.21,
        meaningful_discrimination=0.31,
        dereg_risk_proxy=0.16,
    )

    rules = evaluate_hard_rules(snapshot, bundle)

    assert "elevated_yield_small_pool_caps_confidence" in rules.activated
    assert rules.confidence_cap is not None and rules.confidence_cap <= 0.52


def test_extreme_yield_small_pool_caps_mispricing():
    snapshot = _snapshot(
        active_neurons_7d=6,
        tao_in_pool=700.0,
        emission_per_block_tao=0.04,
        immunity_period=10,
    )
    bundle = _bundle(
        active_ratio=0.18,
        participation_breadth=0.14,
        slippage_10_tao=0.06,
        slippage_50_tao=0.13,
        validator_dominance=0.83,
        incentive_concentration=0.86,
        market_structure_floor=0.39,
        validator_weight_entropy=0.46,
        cross_validator_disagreement=0.20,
        meaningful_discrimination=0.24,
        dereg_risk_proxy=0.22,
    )

    rules = evaluate_hard_rules(snapshot, bundle)

    assert "extreme_yield_small_pool_caps_mispricing" in rules.activated
    assert rules.mispricing_cap is not None and rules.mispricing_cap <= 0.18
    assert rules.fragility_floor is not None and rules.fragility_floor >= 0.76


def test_fragile_repricing_blocks_top_mispricing():
    snapshot = _snapshot(
        active_neurons_7d=6,
        tao_in_pool=5_500.0,
        emission_per_block_tao=0.12,
        immunity_period=10,
    )
    bundle = _bundle(
        active_ratio=0.22,
        participation_breadth=0.18,
        slippage_10_tao=0.03,
        slippage_50_tao=0.08,
        validator_dominance=0.79,
        incentive_concentration=0.81,
        market_structure_floor=0.52,
        validator_weight_entropy=0.50,
        cross_validator_disagreement=0.22,
        meaningful_discrimination=0.28,
        dereg_risk_proxy=0.18,
    )

    rules = evaluate_hard_rules(snapshot, bundle)

    assert "fragile_repricing_blocks_top_mispricing" in rules.activated
    assert rules.mispricing_cap is not None and rules.mispricing_cap <= 0.26
    assert rules.confidence_cap is not None and rules.confidence_cap <= 0.48


def test_inactive_subnet_forces_dereg_risk():
    snapshot = _snapshot(
        tao_in_pool=5000.0,
        emission_per_block_tao=0.01,
        active_neurons_7d=1,
        immunity_period=0,
    )
    bundle = _bundle(
        active_ratio=0.02,
        slippage_10_tao=0.01,
        slippage_50_tao=0.05,
        validator_dominance=0.3,
        incentive_concentration=0.3,
        validator_weight_entropy=0.4,
        cross_validator_disagreement=0.3,
        meaningful_discrimination=0.5,
        dereg_risk_proxy=0.8,
    )
    rules = evaluate_hard_rules(snapshot, bundle)
    axes = AxisScores(
        intrinsic_quality=0.8,
        economic_sustainability=0.8,
        reflexivity=0.2,
        stress_robustness=0.8,
        opportunity_gap=0.3,
    )
    label, thesis = assign_label(axes, bundle, _stress(0.05, robustness=0.8), rules)
    assert label == "Dereg Risk"
    assert "replacement risk" in thesis


def test_thin_liquidity_forces_overrewarded_label():
    snapshot = _snapshot(
        tao_in_pool=30.0,
        emission_per_block_tao=0.02,
        active_neurons_7d=9,
        immunity_period=10,
    )
    bundle = _bundle(
        active_ratio=0.9,
        slippage_10_tao=0.4,
        slippage_50_tao=0.55,
        validator_dominance=0.35,
        incentive_concentration=0.35,
        validator_weight_entropy=0.55,
        cross_validator_disagreement=0.25,
        meaningful_discrimination=0.45,
        dereg_risk_proxy=0.1,
    )
    rules = evaluate_hard_rules(snapshot, bundle)
    axes = AxisScores(
        intrinsic_quality=0.7,
        economic_sustainability=0.7,
        reflexivity=0.55,
        stress_robustness=0.35,
        opportunity_gap=-0.1,
    )
    label, _ = assign_label(axes, bundle, _stress(0.22, robustness=0.35), rules)
    assert label == "Overrewarded"


def test_concentration_alone_does_not_force_overrewarded():
    snapshot = _snapshot(
        tao_in_pool=5000.0,
        emission_per_block_tao=0.03,
        active_neurons_7d=8,
        immunity_period=10,
    )
    bundle = _bundle(
        active_ratio=0.8,
        slippage_10_tao=0.02,
        slippage_50_tao=0.08,
        validator_dominance=0.7,
        incentive_concentration=0.7,
        validator_weight_entropy=0.5,
        cross_validator_disagreement=0.2,
        meaningful_discrimination=0.4,
        dereg_risk_proxy=0.1,
    )
    rules = evaluate_hard_rules(snapshot, bundle)
    axes = AxisScores(
        intrinsic_quality=0.35,
        economic_sustainability=0.5,
        reflexivity=0.3,
        stress_robustness=0.3,
        opportunity_gap=0.05,
    )
    label, _ = assign_label(axes, bundle, _stress(0.21, robustness=0.3), rules)
    assert label == "Evidence Limited"


def test_consensus_hollow_forces_consensus_hollow_label():
    snapshot = _snapshot(
        tao_in_pool=5000.0,
        emission_per_block_tao=0.01,
        active_neurons_7d=8,
        unique_coldkeys=8,
        top3_stake_fraction=0.2,
    )
    bundle = _bundle(
        active_ratio=0.8,
        slippage_10_tao=0.01,
        slippage_50_tao=0.05,
        validator_dominance=0.2,
        incentive_concentration=0.2,
        validator_weight_entropy=0.96,
        cross_validator_disagreement=0.01,
        meaningful_discrimination=0.04,
        dereg_risk_proxy=0.1,
    )
    rules = evaluate_hard_rules(snapshot, bundle)
    axes = AxisScores(
        intrinsic_quality=0.7,
        economic_sustainability=0.7,
        reflexivity=0.2,
        stress_robustness=0.7,
        opportunity_gap=0.2,
    )
    label, _ = assign_label(axes, bundle, _stress(0.1, robustness=0.7), rules)
    assert label == "Consensus Hollow"


def test_high_quality_resilient_case_can_escape_evidence_limited():
    bundle = FeatureBundle(
        raw={
            "market_relevance_proxy": 0.48,
            "thesis_confidence": 0.46,
            "market_confidence": 0.50,
            "data_confidence": 0.48,
            "crowding_proxy": 0.18,
            "validator_dominance": 0.28,
            "incentive_concentration": 0.30,
            "price_response_lag_to_quality_shift": 0.02,
            "emission_to_sticky_usage_conversion": 0.0,
            "post_incentive_retention": 0.0,
        },
        core_blocks={
            "fundamental_health": 0.63,
            "market_legitimacy": 0.48,
        },
    )
    signals = PrimarySignals(
        fundamental_quality=0.68,
        mispricing_signal=0.24,
        fragility_risk=0.30,
        signal_confidence=0.49,
    )

    label, thesis = assign_label(
        signals,
        bundle,
        _stress(0.12, robustness=0.72),
        HardRuleResult(activated=[]),
    )

    assert label == "Quality Leader"
    assert "Quality and resilience" in thesis


def test_deep_liquid_concentration_uses_watchlist_caps_not_harsh_cap():
    snapshot = _snapshot(
        tao_in_pool=150000.0,
        emission_per_block_tao=0.04,
        active_neurons_7d=10,
        unique_coldkeys=7,
        n_validators=5,
        immunity_period=10,
    )
    bundle = _bundle(
        active_ratio=0.5,
        participation_breadth=0.52,
        slippage_10_tao=0.01,
        slippage_50_tao=0.02,
        validator_dominance=0.92,
        incentive_concentration=0.65,
        concentration_delta=-0.03,
        validator_weight_entropy=0.55,
        cross_validator_disagreement=0.18,
        meaningful_discrimination=0.32,
        dereg_risk_proxy=0.12,
    )

    rules = evaluate_hard_rules(snapshot, bundle)

    assert "concentration_caps_fundamental_quality" in rules.activated
    assert "liquid_flagship_concentration_watchlist" in rules.activated
    assert rules.quality_cap == 0.60
    assert rules.fragility_floor == 0.52


def test_market_relevant_concentration_uses_watchlist_caps():
    snapshot = _snapshot(
        tao_in_pool=25_000.0,
        emission_per_block_tao=0.03,
        active_neurons_7d=7,
        unique_coldkeys=5,
        n_validators=4,
        immunity_period=10,
    )
    bundle = _bundle(
        active_ratio=0.35,
        participation_breadth=0.34,
        market_relevance_proxy=0.66,
        market_structure_floor=0.74,
        crowding_proxy=0.18,
        overreaction_score=0.04,
        data_coverage=0.62,
        update_freshness=0.72,
        slippage_10_tao=0.02,
        slippage_50_tao=0.05,
        validator_dominance=0.82,
        incentive_concentration=0.66,
        concentration_delta=0.01,
        validator_weight_entropy=0.52,
        cross_validator_disagreement=0.18,
        meaningful_discrimination=0.31,
        dereg_risk_proxy=0.15,
    )

    rules = evaluate_hard_rules(snapshot, bundle)

    assert "concentration_caps_fundamental_quality" in rules.activated
    assert "market_relevant_concentration_watchlist" in rules.activated
    assert rules.quality_cap == 0.58
    assert rules.fragility_floor == 0.56


def test_resilient_midcap_concentration_uses_softer_watchlist_cap():
    snapshot = _snapshot(
        tao_in_pool=11_000.0,
        emission_per_block_tao=0.025,
        active_neurons_7d=6,
        unique_coldkeys=5,
        n_validators=4,
        immunity_period=10,
    )
    bundle = _bundle(
        active_ratio=0.40,
        participation_breadth=0.28,
        market_relevance_proxy=0.48,
        market_structure_floor=0.60,
        data_coverage=0.64,
        update_freshness=0.70,
        slippage_10_tao=0.025,
        slippage_50_tao=0.06,
        validator_dominance=0.76,
        incentive_concentration=0.73,
        structural_concentration_risk=0.72,
        concentration_delta=0.01,
        validator_weight_entropy=0.48,
        cross_validator_disagreement=0.21,
        meaningful_discrimination=0.29,
        dereg_risk_proxy=0.18,
    )

    rules = evaluate_hard_rules(snapshot, bundle)

    assert "concentration_caps_fundamental_quality" in rules.activated
    assert "resilient_midcap_concentration_watchlist" in rules.activated
    assert rules.quality_cap == 0.54
    assert rules.fragility_floor == 0.58


def test_moderate_concentration_without_other_stress_no_longer_triggers_cap():
    snapshot = _snapshot(
        tao_in_pool=18_000.0,
        emission_per_block_tao=0.03,
        active_neurons_7d=9,
        immunity_period=10,
    )
    bundle = _bundle(
        active_ratio=0.42,
        participation_breadth=0.34,
        market_relevance_proxy=0.52,
        market_structure_floor=0.62,
        crowding_proxy=0.22,
        slippage_10_tao=0.02,
        slippage_50_tao=0.05,
        validator_dominance=0.64,
        incentive_concentration=0.63,
        concentration_delta=0.0,
        validator_weight_entropy=0.52,
        cross_validator_disagreement=0.18,
        meaningful_discrimination=0.31,
        dereg_risk_proxy=0.15,
    )

    rules = evaluate_hard_rules(snapshot, bundle)

    assert "concentration_caps_fundamental_quality" not in rules.activated


def test_signal_fabrication_risk_caps_mispricing_and_confidence():
    snapshot = _snapshot(
        tao_in_pool=6_000.0,
        emission_per_block_tao=0.08,
        active_neurons_7d=6,
        immunity_period=10,
    )
    bundle = _bundle(
        active_ratio=0.28,
        participation_breadth=0.18,
        slippage_10_tao=0.04,
        slippage_50_tao=0.11,
        validator_dominance=0.84,
        incentive_concentration=0.88,
        data_coverage=0.38,
        proxy_reliance_penalty=0.66,
        confidence_thesis_coherence=0.44,
        signal_fabrication_risk=0.71,
        low_evidence_high_conviction=0.49,
        underreaction_score=0.58,
        market_structure_floor=0.48,
    )

    rules = evaluate_hard_rules(snapshot, bundle)

    assert "signal_fabrication_risk_caps_mispricing" in rules.activated
    assert rules.mispricing_cap is not None and rules.mispricing_cap <= 0.36
    assert rules.confidence_cap is not None and rules.confidence_cap <= 0.46


def test_low_evidence_high_conviction_caps_total_score():
    snapshot = _snapshot(
        tao_in_pool=12_000.0,
        emission_per_block_tao=0.05,
        active_neurons_7d=7,
        immunity_period=10,
    )
    bundle = _bundle(
        active_ratio=0.34,
        participation_breadth=0.22,
        slippage_10_tao=0.03,
        slippage_50_tao=0.08,
        validator_dominance=0.72,
        incentive_concentration=0.74,
        data_coverage=0.42,
        proxy_reliance_penalty=0.61,
        confidence_thesis_coherence=0.49,
        signal_fabrication_risk=0.55,
        low_evidence_high_conviction=0.63,
        underreaction_score=0.74,
        market_structure_floor=0.57,
    )

    rules = evaluate_hard_rules(snapshot, bundle)

    assert "low_evidence_high_conviction_caps_total" in rules.activated
    assert rules.mispricing_cap is not None and rules.mispricing_cap <= 0.32
    assert rules.total_cap is not None and rules.total_cap <= 0.40


def test_reflexive_market_structure_caps_confidence():
    snapshot = _snapshot(
        tao_in_pool=18_000.0,
        emission_per_block_tao=0.06,
        active_neurons_7d=7,
        immunity_period=10,
    )
    bundle = _bundle(
        active_ratio=0.26,
        participation_breadth=0.22,
        slippage_10_tao=0.03,
        slippage_50_tao=0.07,
        validator_dominance=0.71,
        incentive_concentration=0.69,
        crowding_proxy=0.66,
        overreaction_score=0.31,
        data_coverage=0.72,
        proxy_reliance_penalty=0.34,
        confidence_thesis_coherence=0.82,
        market_structure_floor=0.59,
    )

    rules = evaluate_hard_rules(snapshot, bundle)

    assert "reflexive_market_structure_caps_confidence" in rules.activated
    assert rules.confidence_cap is not None and rules.confidence_cap <= 0.44
    assert rules.mispricing_cap is not None and rules.mispricing_cap <= 0.36


def test_crowded_repricing_discount_caps_confidence():
    snapshot = _snapshot(
        tao_in_pool=12_000.0,
        emission_per_block_tao=0.05,
        active_neurons_7d=6,
        immunity_period=10,
    )
    bundle = _bundle(
        active_ratio=0.31,
        participation_breadth=0.24,
        slippage_10_tao=0.025,
        slippage_50_tao=0.045,
        validator_dominance=0.66,
        incentive_concentration=0.63,
        crowding_proxy=0.61,
        overreaction_score=0.21,
        data_coverage=0.78,
        proxy_reliance_penalty=0.28,
        confidence_thesis_coherence=0.76,
        market_structure_floor=0.60,
        signal_fabrication_risk=0.44,
    )

    rules = evaluate_hard_rules(snapshot, bundle)

    assert "crowded_repricing_discount_caps_confidence" in rules.activated
    assert rules.confidence_cap is not None and rules.confidence_cap <= 0.40
    assert rules.mispricing_cap is not None and rules.mispricing_cap <= 0.34
    assert rules.fragility_floor is not None and rules.fragility_floor >= 0.68


def test_crowded_structure_evidence_watchlist_caps_confidence_and_sets_fragility_floor():
    snapshot = _snapshot(
        tao_in_pool=120_000.0,
        emission_per_block_tao=0.032,
        active_neurons_7d=7,
        immunity_period=10,
    )
    bundle = _bundle(
        active_ratio=0.52,
        participation_breadth=0.58,
        slippage_10_tao=0.015,
        slippage_50_tao=0.02,
        validator_dominance=0.64,
        incentive_concentration=0.62,
        crowding_proxy=0.66,
        overreaction_score=0.16,
        market_relevance_proxy=0.78,
        market_structure_floor=0.74,
        data_coverage=0.72,
        proxy_reliance_penalty=0.24,
        confidence_thesis_coherence=0.84,
        signal_fabrication_risk=0.20,
        low_evidence_high_conviction=0.12,
        underreaction_score=0.18,
    )
    bundle.core_blocks["crowded_structure_watchlist"] = 0.64
    rules = evaluate_hard_rules(snapshot, bundle)
    adjusted = apply_rule_caps(
        PrimarySignals(
            fundamental_quality=0.58,
            mispricing_signal=0.40,
            fragility_risk=0.55,
            signal_confidence=0.63,
        ),
        rules,
    )

    assert "crowded_structure_evidence_watchlist" in rules.activated
    assert adjusted.signal_confidence <= 0.54
    assert adjusted.fragility_risk >= 0.66


def test_severe_market_structure_breach_caps_microstructure_setups():
    snapshot = _snapshot(
        tao_in_pool=700.0,
        alpha_in_pool=5.0,
        emission_per_block_tao=0.03,
        active_neurons_7d=2,
        unique_coldkeys=2,
        n_validators=2,
        immunity_period=10,
    )
    bundle = _bundle(
        active_ratio=0.2,
        participation_breadth=0.2,
        market_structure_floor=0.30,
        market_relevance_proxy=0.22,
        data_coverage=0.85,
        update_freshness=0.85,
        slippage_10_tao=0.09,
        slippage_50_tao=0.18,
        validator_dominance=0.35,
        incentive_concentration=0.35,
        validator_weight_entropy=0.45,
        cross_validator_disagreement=0.18,
        meaningful_discrimination=0.3,
        dereg_risk_proxy=0.15,
    )

    rules = evaluate_hard_rules(snapshot, bundle)

    assert "market_structure_floor_blocks_top_rank" in rules.activated
    assert rules.quality_cap == 0.34
    assert rules.mispricing_cap == 0.18
    assert rules.fragility_floor == 0.78
    assert rules.total_cap is not None and rules.total_cap <= 0.34


def test_moderate_market_structure_breach_uses_watchlist_caps():
    snapshot = _snapshot(
        tao_in_pool=5_000.0,
        alpha_in_pool=100.0,
        emission_per_block_tao=0.03,
        active_neurons_7d=4,
        unique_coldkeys=3,
        n_validators=3,
        immunity_period=10,
    )
    bundle = _bundle(
        active_ratio=0.28,
        participation_breadth=0.26,
        market_structure_floor=0.39,
        market_relevance_proxy=0.34,
        data_coverage=0.85,
        update_freshness=0.85,
        slippage_10_tao=0.08,
        slippage_50_tao=0.13,
        validator_dominance=0.42,
        incentive_concentration=0.38,
        validator_weight_entropy=0.45,
        cross_validator_disagreement=0.18,
        meaningful_discrimination=0.3,
        dereg_risk_proxy=0.15,
    )

    rules = evaluate_hard_rules(snapshot, bundle)

    assert "market_structure_floor_watchlist" in rules.activated
    assert rules.quality_cap == 0.42
    assert rules.mispricing_cap == 0.26
    assert rules.fragility_floor == 0.72


def test_liquid_hyped_subnet_can_be_crowded_reflexive():
    snapshot = _snapshot(
        tao_in_pool=100000.0,
        emission_per_block_tao=0.03,
        active_neurons_7d=7,
        unique_coldkeys=30,
        top3_stake_fraction=0.58,
        immunity_period=10,
    )
    bundle = _bundle(
        active_ratio=0.2,
        slippage_10_tao=0.02,
        slippage_50_tao=0.09,
        validator_dominance=0.58,
        incentive_concentration=0.61,
        validator_weight_entropy=0.52,
        cross_validator_disagreement=0.22,
        meaningful_discrimination=0.36,
        dereg_risk_proxy=0.18,
    )
    rules = evaluate_hard_rules(snapshot, bundle)
    axes = AxisScores(
        intrinsic_quality=0.56,
        economic_sustainability=0.69,
        reflexivity=0.74,
        stress_robustness=0.57,
        opportunity_gap=-0.04,
    )
    label, thesis = assign_label(axes, bundle, _stress(0.23, robustness=0.57), rules)
    assert label == "Crowded Reflexive"
    assert "crowded" in thesis.lower()


def test_label_logic_can_use_v2_blocks_for_compounding_quality():
    bundle = FeatureBundle(
        raw={
            "validator_dominance": 0.22,
            "incentive_concentration": 0.24,
            "price_response_lag_to_quality_shift": 0.18,
            "emission_to_sticky_usage_conversion": 0.11,
            "post_incentive_retention": 0.12,
            "crowding_proxy": 0.18,
            "dereg_risk_proxy": 0.10,
        },
        core_blocks={
            "fundamental_health": 0.78,
            "opportunity_underreaction": 0.71,
            "market_legitimacy": 0.66,
        },
        base_components={
            "data_confidence": 0.64,
            "market_confidence": 0.67,
            "thesis_confidence": 0.69,
        },
    )
    signals = PrimarySignals(
        fundamental_quality=0.78,
        mispricing_signal=0.70,
        fragility_risk=0.26,
        signal_confidence=0.64,
    )

    label, thesis = assign_label(signals, bundle, _stress(0.08, robustness=0.82), HardRuleResult(activated=[]))

    assert label == "Compounding Quality"
    assert "compounding" in thesis.lower()


def test_label_logic_uses_v2_confidence_artifacts_for_evidence_limited():
    bundle = FeatureBundle(
        raw={
            "validator_dominance": 0.20,
            "incentive_concentration": 0.20,
            "price_response_lag_to_quality_shift": 0.12,
            "emission_to_sticky_usage_conversion": 0.08,
            "post_incentive_retention": 0.08,
            "crowding_proxy": 0.18,
            "dereg_risk_proxy": 0.18,
        },
        core_blocks={
            "fundamental_health": 0.62,
            "opportunity_underreaction": 0.60,
            "market_legitimacy": 0.55,
        },
        base_components={
            "data_confidence": 0.52,
            "market_confidence": 0.48,
            "thesis_confidence": 0.22,
        },
    )
    signals = PrimarySignals(
        fundamental_quality=0.64,
        mispricing_signal=0.61,
        fragility_risk=0.30,
        signal_confidence=0.47,
    )

    label, thesis = assign_label(signals, bundle, _stress(0.10, robustness=0.74), HardRuleResult(activated=[]))

    assert label == "Evidence Limited"
    assert "evidence quality" in thesis.lower()
