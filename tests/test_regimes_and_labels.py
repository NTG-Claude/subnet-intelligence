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
