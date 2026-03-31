from collectors.models import RawSubnetSnapshot
from features.types import AxisScores, FeatureBundle
from labels.engine import assign_label
from regimes.hard_rules import evaluate_hard_rules
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


def test_micro_pool_apy_forces_overrewarded_structure_rule():
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
    assert rules.force_label == "Overrewarded Structure"
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


def test_inactive_subnet_forces_dereg_candidate():
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
    assert label == "Dereg Candidate"
    assert "replacement risk" in thesis


def test_thin_liquidity_forces_overrewarded_structure_label():
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
    assert label == "Overrewarded Structure"


def test_concentration_alone_does_not_force_overrewarded_structure():
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
    assert label == "Under Review"


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
    assert rules.quality_cap == 0.52
    assert rules.fragility_floor == 0.58


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
    assert rules.quality_cap == 0.56
    assert rules.fragility_floor == 0.60


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
    assert rules.mispricing_cap == 0.24
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
    assert rules.mispricing_cap == 0.34
    assert rules.fragility_floor == 0.70


def test_liquid_hyped_subnet_can_be_reflexive_crowded_trade():
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
    assert label == "Reflexive Crowded Trade"
    assert "crowded" in thesis.lower()
