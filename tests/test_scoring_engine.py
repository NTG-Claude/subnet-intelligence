from collectors.models import HistoricalFeaturePoint, RawSubnetSnapshot
from features.types import AxisScores
from features.types import FeatureBundle, PrimarySignals
from regimes.hard_rules import HardRuleResult
from scoring.engine import _apply_total_cap, _ranking_priority_score, build_scores


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

    assert artifacts.score > 40.0
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
