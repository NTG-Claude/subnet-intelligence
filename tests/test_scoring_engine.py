import pytest

from collectors.models import RepoActivitySnapshot
from collectors.models import HistoricalFeaturePoint, RawSubnetSnapshot
from features.types import AxisScores
from features.types import FeatureBundle, PrimarySignals
from features.types import ConditionedSnapshot
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
from stress.scenarios import run_stress_tests


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
    assert artifacts.label == "Evidence Limited"
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


def test_stabilize_primary_with_history_allows_larger_breakaway_when_runtime_is_reliable():
    snapshot = RawSubnetSnapshot(
        netuid=17,
        current_block=1000,
        history=[
            HistoricalFeaturePoint(
                timestamp="2026-03-31T11:46:31+00:00",
                fundamental_quality=0.22,
                mispricing_signal=0.18,
                fragility_risk=0.78,
                signal_confidence=0.28,
            )
        ],
    )
    current = PrimarySignals(
        fundamental_quality=0.62,
        mispricing_signal=0.48,
        fragility_risk=0.42,
        signal_confidence=0.60,
    )
    bundle = FeatureBundle(
        raw={"price_signal_reliability": 1.0},
        conditioned=ConditionedSnapshot(
            reliability={
                "market_data_reliability": 1.0,
                "validator_data_reliability": 1.0,
                "external_data_reliability": 0.8,
            }
        ),
    )

    stabilized = _stabilize_primary_with_history(snapshot, current, bundle)

    assert stabilized.fundamental_quality > snapshot.history[0].fundamental_quality + PRIMARY_SIGNAL_DRIFT_CAPS["fundamental_quality"]
    assert stabilized.mispricing_signal > snapshot.history[0].mispricing_signal + PRIMARY_SIGNAL_DRIFT_CAPS["mispricing_signal"]
    assert stabilized.fragility_risk < snapshot.history[0].fragility_risk - PRIMARY_SIGNAL_DRIFT_CAPS["fragility_risk"]


def test_external_repo_continuity_supports_confidence_beyond_empty_30d_window():
    base_kwargs = dict(
        current_block=1000,
        n_total=128,
        yuma_neurons=128,
        active_neurons_7d=96,
        active_validators_7d=8,
        total_stake_tao=1_500_000.0,
        unique_coldkeys=48,
        top3_stake_fraction=0.52,
        emission_per_block_tao=0.08,
        incentive_scores=[0.12, 0.10, 0.09, 0.08],
        n_validators=12,
        tao_in_pool=42_000.0,
        alpha_in_pool=1_200_000.0,
        alpha_price_tao=0.035,
        coldkey_stakes=[200_000.0, 150_000.0, 120_000.0],
        validator_stakes=[180_000.0] * 12,
        validator_weight_matrix=[],
        validator_bond_matrix=[],
        last_update_blocks=[5, 8, 13],
        yuma_mask=[True] * 12,
        mechanism_ids=[0],
        immunity_period=0,
        registration_allowed=True,
        target_regs_per_interval=2,
        min_burn=0.0,
        max_burn=0.0,
        difficulty=0.0,
        history=[
            HistoricalFeaturePoint(
                timestamp="2026-03-20T00:00:00+00:00",
                alpha_price_tao=0.034,
                tao_in_pool=41_500.0,
                emission_per_block_tao=0.08,
                active_ratio=0.74,
                participation_breadth=0.42,
                validator_participation=0.68,
                incentive_distribution_quality=0.61,
                concentration_proxy=0.44,
                liquidity_thinness=0.05,
                market_relevance_proxy=0.62,
                market_structure_floor=0.71,
                intrinsic_quality=0.58,
                economic_sustainability=0.61,
                reflexivity=0.33,
                stress_robustness=0.66,
                opportunity_gap=0.05,
                fundamental_quality=0.61,
                mispricing_signal=0.41,
                fragility_risk=0.29,
                signal_confidence=0.48,
            )
        ],
    )
    no_repo_snapshot = RawSubnetSnapshot(netuid=201, **base_kwargs)
    continuity_repo_snapshot = RawSubnetSnapshot(
        netuid=202,
        github=RepoActivitySnapshot(
            github_url="https://github.com/example/subnet",
            owner="example",
            repo="subnet",
            source_status="active_repo",
            commits_30d=0,
            contributors_30d=0,
            commits_90d=24,
            contributors_90d=3,
            commits_180d=72,
            contributors_180d=6,
            last_push="2026-03-18T00:00:00+00:00",
            last_commit_at="2026-03-18T00:00:00+00:00",
        ),
        **base_kwargs,
    )

    artifacts = build_scores([no_repo_snapshot, continuity_repo_snapshot])

    assert artifacts[202].primary.signal_confidence > artifacts[201].primary.signal_confidence


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


def test_ranking_priority_uses_v2_opportunity_block_even_if_legacy_raw_differs():
    signals = PrimarySignals(
        fundamental_quality=0.58,
        mispricing_signal=0.40,
        fragility_risk=0.42,
        signal_confidence=0.57,
    )
    stronger_bundle = FeatureBundle(
        raw={"market_relevance_proxy": 0.35},
        core_blocks={"opportunity_underreaction": 0.72},
    )
    weaker_bundle = FeatureBundle(
        raw={"market_relevance_proxy": 0.35},
        core_blocks={"opportunity_underreaction": 0.28},
    )

    assert _ranking_priority_score(signals, stronger_bundle) > _ranking_priority_score(signals, weaker_bundle)


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


def test_stress_tests_prefer_v2_components_over_raw_proxy_gaps():
    snapshot = RawSubnetSnapshot(netuid=21, current_block=1000)
    axes = AxisScores(
        intrinsic_quality=0.62,
        economic_sustainability=0.58,
        reflexivity=0.34,
        stress_robustness=0.64,
        opportunity_gap=0.12,
    )
    resilient_bundle = FeatureBundle(
        raw={
            "active_ratio": 0.05,
            "meaningful_discrimination": 0.10,
            "liquidity_thinness": 0.90,
            "validator_dominance": 0.80,
            "crowding_proxy": 0.75,
            "market_relevance_proxy": 0.20,
        },
        base_components={
            "participation_health": 0.76,
            "validator_health": 0.72,
            "liquidity_health": 0.74,
        },
        core_blocks={
            "fundamental_health": 0.70,
            "market_confidence": 0.68,
            "market_legitimacy": 0.65,
            "concentration_risk": 0.22,
            "crowding_level": 0.18,
            "thin_liquidity_risk": 0.26,
            "weak_market_structure": 0.24,
        },
    )
    fragile_bundle = FeatureBundle(
        raw=resilient_bundle.raw.copy(),
        base_components={
            "participation_health": 0.28,
            "validator_health": 0.26,
            "liquidity_health": 0.24,
        },
        core_blocks={
            "fundamental_health": 0.30,
            "market_confidence": 0.25,
            "market_legitimacy": 0.22,
            "concentration_risk": 0.84,
            "crowding_level": 0.78,
            "thin_liquidity_risk": 0.82,
            "weak_market_structure": 0.80,
        },
    )

    resilient = run_stress_tests(snapshot, resilient_bundle, axes)
    fragile = run_stress_tests(snapshot, fragile_bundle, axes)

    assert resilient.max_drawdown < fragile.max_drawdown
    assert resilient.robustness > fragile.robustness


def test_stress_tests_remain_stable_with_legacy_raw_fallbacks():
    snapshot = RawSubnetSnapshot(netuid=22, current_block=1000)
    axes = AxisScores(
        intrinsic_quality=0.55,
        economic_sustainability=0.51,
        reflexivity=0.40,
        stress_robustness=0.57,
        opportunity_gap=0.05,
    )
    bundle = FeatureBundle(
        raw={
            "active_ratio": 0.24,
            "meaningful_discrimination": 0.33,
            "liquidity_thinness": 0.42,
            "validator_dominance": 0.36,
            "incentive_concentration": 0.31,
            "crowding_proxy": 0.28,
            "market_relevance_proxy": 0.44,
        }
    )

    result = run_stress_tests(snapshot, bundle, axes)

    assert len(result.scenarios) == 7
    assert 0.0 <= result.max_drawdown <= 1.0
    assert 0.0 <= result.robustness <= 1.0
    assert result.fragility_class in {"robust", "watchlist", "fragile"}
