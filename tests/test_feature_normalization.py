from collectors.models import HistoricalFeaturePoint, RawSubnetSnapshot
from features.metrics import compute_raw_features, normalize_features


def _snapshot(**overrides) -> RawSubnetSnapshot:
    base = RawSubnetSnapshot(
        netuid=1,
        current_block=1000,
        n_total=10,
        yuma_neurons=10,
        active_neurons_7d=5,
        total_stake_tao=1000.0,
        unique_coldkeys=5,
        top3_stake_fraction=0.4,
        emission_per_block_tao=0.05,
        incentive_scores=[0.6, 0.4],
        n_validators=5,
        tao_in_pool=1000.0,
        alpha_in_pool=100.0,
        alpha_price_tao=10.0,
        coldkey_stakes=[600.0, 400.0],
        validator_stakes=[300.0, 250.0, 200.0, 150.0, 100.0],
        validator_weight_matrix=[],
        validator_bond_matrix=[],
        last_update_blocks=[1000] * 10,
        yuma_mask=[True] * 10,
        mechanism_ids=[0] * 10,
        immunity_period=10,
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


def test_missing_consensus_metrics_are_neutral_not_zeroed():
    bundles = normalize_features([compute_raw_features(_snapshot())])
    debug = bundles[0].metrics
    assert debug["validator_weight_entropy"].normalized == 0.5
    assert debug["cross_validator_disagreement"].normalized == 0.5
    assert debug["meaningful_discrimination"].normalized == 0.5


def test_mispricing_temporal_features_follow_quality_history_not_active_history():
    snapshot = _snapshot(
        active_neurons_7d=5,
        unique_coldkeys=8,
        n_validators=6,
        incentive_scores=[0.4, 0.3, 0.3],
        alpha_price_tao=10.0,
        history=[
            HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=10.0, active_ratio=0.9, fundamental_quality=0.20),
            HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=10.0, active_ratio=0.9, fundamental_quality=0.28),
            HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=10.0, active_ratio=0.9, fundamental_quality=0.38),
        ],
    )

    bundle = compute_raw_features(snapshot)

    assert bundle.raw["quality_acceleration"] is not None
    assert bundle.raw["quality_acceleration"] > 0
    assert bundle.raw["price_response_lag_to_quality_shift"] > 0


def test_market_relevance_proxy_rewards_scaled_participating_subnets():
    flagship = compute_raw_features(
        _snapshot(
            active_neurons_7d=8,
            unique_coldkeys=9,
            n_validators=7,
            tao_in_pool=75_000.0,
        )
    )
    micro = compute_raw_features(
        _snapshot(
            active_neurons_7d=2,
            unique_coldkeys=2,
            n_validators=2,
            tao_in_pool=120.0,
        )
    )

    assert flagship.raw["market_relevance_proxy"] > micro.raw["market_relevance_proxy"]


def test_market_structure_floor_penalizes_thin_microstructure():
    robust = compute_raw_features(
        _snapshot(
            active_neurons_7d=8,
            unique_coldkeys=8,
            n_validators=7,
            tao_in_pool=40_000.0,
            alpha_in_pool=12_000.0,
        )
    )
    thin = compute_raw_features(
        _snapshot(
            active_neurons_7d=2,
            unique_coldkeys=2,
            n_validators=2,
            tao_in_pool=600.0,
            alpha_in_pool=4.0,
        )
    )

    assert robust.raw["market_structure_floor"] > thin.raw["market_structure_floor"]


def test_confidence_integrity_and_coherence_penalize_fragile_crowded_setups():
    robust = compute_raw_features(
        _snapshot(
            active_neurons_7d=8,
            unique_coldkeys=8,
            n_validators=7,
            tao_in_pool=45_000.0,
            alpha_in_pool=12_000.0,
            history=[
                HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=10.0, tao_in_pool=40_000.0, active_ratio=0.6, fundamental_quality=0.55),
                HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=10.2, tao_in_pool=42_000.0, active_ratio=0.62, fundamental_quality=0.58),
                HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=10.3, tao_in_pool=44_000.0, active_ratio=0.65, fundamental_quality=0.62),
            ],
        )
    )
    fragile = compute_raw_features(
        _snapshot(
            active_neurons_7d=3,
            unique_coldkeys=2,
            n_validators=2,
            tao_in_pool=5_400.0,
            alpha_in_pool=90.0,
            top3_stake_fraction=0.82,
            incentive_scores=[0.9, 0.1],
            history=[
                HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=6.0, tao_in_pool=4_800.0, active_ratio=0.28, fundamental_quality=0.42),
                HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=7.4, tao_in_pool=5_000.0, active_ratio=0.27, fundamental_quality=0.41),
                HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=8.8, tao_in_pool=5_200.0, active_ratio=0.26, fundamental_quality=0.39),
            ],
        )
    )

    assert robust.raw["confidence_market_integrity"] > fragile.raw["confidence_market_integrity"]
    assert robust.raw["confidence_thesis_coherence"] > fragile.raw["confidence_thesis_coherence"]

