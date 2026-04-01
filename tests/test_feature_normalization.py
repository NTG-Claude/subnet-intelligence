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
    assert debug["bond_responsiveness"].normalized == 0.5
    assert debug["validator_weight_entropy"].weight == 0.0
    assert debug["cross_validator_disagreement"].weight == 0.0
    assert debug["meaningful_discrimination"].weight == 0.0
    assert debug["bond_responsiveness"].weight == 0.0


def test_data_coverage_reflects_live_signal_family_availability():
    rich = compute_raw_features(
        _snapshot(
            active_neurons_7d=8,
            unique_coldkeys=8,
            n_validators=7,
            tao_in_pool=40_000.0,
            alpha_in_pool=10_000.0,
            alpha_price_tao=10.2,
            github=None,
            history=[
                HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=10.0, tao_in_pool=36_000.0, active_ratio=0.50, fundamental_quality=0.49),
                HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=10.0, tao_in_pool=38_000.0, active_ratio=0.55, fundamental_quality=0.56),
                HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=10.1, tao_in_pool=39_000.0, active_ratio=0.60, fundamental_quality=0.61),
            ],
        )
    )
    poor = compute_raw_features(
        _snapshot(
            active_neurons_7d=2,
            unique_coldkeys=2,
            n_validators=2,
            tao_in_pool=0.0,
            alpha_in_pool=0.0,
            alpha_price_tao=0.0,
            history=[],
        )
    )

    assert rich.raw["market_signal_coverage"] > poor.raw["market_signal_coverage"]
    assert rich.raw["history_signal_coverage"] > poor.raw["history_signal_coverage"]
    assert rich.raw["data_coverage"] > poor.raw["data_coverage"]
    assert rich.raw["consensus_signal_gap"] == 1.0


def test_history_depth_score_is_not_saturated_by_short_sparse_history():
    sparse = compute_raw_features(
        _snapshot(
            history=[
                HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=10.0),
                HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=10.1),
                HistoricalFeaturePoint(timestamp="2026-04-01T00:00:00+00:00", alpha_price_tao=10.2),
            ],
        )
    )
    dense = compute_raw_features(
        _snapshot(
            history=[
                HistoricalFeaturePoint(
                    timestamp=f"2026-03-{day:02d}T00:00:00+00:00",
                    alpha_price_tao=9.0 + day * 0.03,
                    tao_in_pool=900.0 + day * 12.0,
                    emission_per_block_tao=0.045 + day * 0.0002,
                    active_ratio=0.40 + day * 0.005,
                    concentration_proxy=max(0.2, 0.65 - day * 0.01),
                    liquidity_thinness=max(0.01, 0.20 - day * 0.01),
                    fundamental_quality=0.42 + day * 0.006,
                )
                for day in range(1, 16)
            ],
        )
    )

    assert sparse.raw["history_depth_score"] < 0.5
    assert dense.raw["history_depth_score"] > sparse.raw["history_depth_score"]


def test_update_freshness_rewards_recent_updates_with_age_curve():
    recent = compute_raw_features(
        _snapshot(
            current_block=200_000,
            yuma_neurons=128,
            n_total=128,
            last_update_blocks=[199_900] * 24 + [198_000] * 8,
        )
    )
    stale = compute_raw_features(
        _snapshot(
            current_block=200_000,
            yuma_neurons=128,
            n_total=128,
            last_update_blocks=[160_000] * 24 + [120_000] * 8,
        )
    )

    assert recent.raw["update_freshness"] > stale.raw["update_freshness"]
    assert recent.raw["update_freshness"] > 0.2


def test_flagship_validator_activity_uses_validator_denominator_not_total_yuma():
    bundle = compute_raw_features(
        _snapshot(
            n_total=256,
            yuma_neurons=256,
            active_neurons_7d=4,
            active_validators_7d=4,
            n_validators=4,
            unique_coldkeys=99,
            tao_in_pool=120_000.0,
            alpha_in_pool=15_000.0,
        )
    )

    assert bundle.raw["active_ratio"] == 1.0
    assert bundle.raw["validator_participation"] == 0.25


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


def test_quality_history_series_can_use_historic_structure_components():
    snapshot = _snapshot(
        active_neurons_7d=7,
        unique_coldkeys=8,
        n_validators=7,
        tao_in_pool=42_000.0,
        alpha_in_pool=12_500.0,
        alpha_price_tao=10.0,
        history=[
            HistoricalFeaturePoint(
                timestamp="2026-03-29T00:00:00+00:00",
                alpha_price_tao=10.0,
                tao_in_pool=34_000.0,
                active_ratio=0.48,
                participation_breadth=0.24,
                validator_participation=0.32,
                incentive_distribution_quality=0.44,
                market_structure_floor=0.40,
                fundamental_quality=0.42,
            ),
            HistoricalFeaturePoint(
                timestamp="2026-03-30T00:00:00+00:00",
                alpha_price_tao=10.0,
                tao_in_pool=37_000.0,
                active_ratio=0.52,
                participation_breadth=0.30,
                validator_participation=0.38,
                incentive_distribution_quality=0.48,
                market_structure_floor=0.47,
                fundamental_quality=0.42,
            ),
            HistoricalFeaturePoint(
                timestamp="2026-03-31T00:00:00+00:00",
                alpha_price_tao=10.0,
                tao_in_pool=40_000.0,
                active_ratio=0.56,
                participation_breadth=0.36,
                validator_participation=0.44,
                incentive_distribution_quality=0.52,
                market_structure_floor=0.55,
                fundamental_quality=0.42,
            ),
        ],
    )

    bundle = compute_raw_features(snapshot)

    assert bundle.raw["quality_acceleration"] is not None
    assert bundle.raw["quality_acceleration"] > 0
    assert bundle.raw["price_response_lag_to_quality_shift"] > 0


def test_post_incentive_retention_rewards_broader_improving_structure():
    retained = compute_raw_features(
        _snapshot(
            active_neurons_7d=7,
            active_validators_7d=7,
            unique_coldkeys=8,
            n_validators=7,
            tao_in_pool=38_000.0,
            alpha_in_pool=11_000.0,
            emission_per_block_tao=0.04,
            history=[
                HistoricalFeaturePoint(
                    timestamp="2026-03-29T00:00:00+00:00",
                    alpha_price_tao=10.0,
                    tao_in_pool=31_000.0,
                    emission_per_block_tao=0.044,
                    active_ratio=0.44,
                    participation_breadth=0.22,
                    validator_participation=0.28,
                    incentive_distribution_quality=0.43,
                    market_structure_floor=0.39,
                ),
                HistoricalFeaturePoint(
                    timestamp="2026-03-30T00:00:00+00:00",
                    alpha_price_tao=10.0,
                    tao_in_pool=34_000.0,
                    emission_per_block_tao=0.042,
                    active_ratio=0.50,
                    participation_breadth=0.29,
                    validator_participation=0.35,
                    incentive_distribution_quality=0.47,
                    market_structure_floor=0.47,
                ),
                HistoricalFeaturePoint(
                    timestamp="2026-03-31T00:00:00+00:00",
                    alpha_price_tao=10.1,
                    tao_in_pool=36_000.0,
                    emission_per_block_tao=0.041,
                    active_ratio=0.56,
                    participation_breadth=0.35,
                    validator_participation=0.43,
                    incentive_distribution_quality=0.52,
                    market_structure_floor=0.55,
                ),
            ],
        )
    )
    subsidized = compute_raw_features(
        _snapshot(
            active_neurons_7d=4,
            active_validators_7d=1,
            unique_coldkeys=3,
            n_validators=3,
            tao_in_pool=8_000.0,
            alpha_in_pool=140.0,
            alpha_price_tao=15.0,
            emission_per_block_tao=0.07,
            history=[
                HistoricalFeaturePoint(
                    timestamp="2026-03-29T00:00:00+00:00",
                    alpha_price_tao=8.5,
                    tao_in_pool=7_700.0,
                    emission_per_block_tao=0.05,
                    active_ratio=0.32,
                    participation_breadth=0.18,
                    validator_participation=0.21,
                    incentive_distribution_quality=0.39,
                    market_structure_floor=0.30,
                ),
                HistoricalFeaturePoint(
                    timestamp="2026-03-30T00:00:00+00:00",
                    alpha_price_tao=9.8,
                    tao_in_pool=7_800.0,
                    emission_per_block_tao=0.06,
                    active_ratio=0.31,
                    participation_breadth=0.18,
                    validator_participation=0.20,
                    incentive_distribution_quality=0.38,
                    market_structure_floor=0.29,
                ),
                HistoricalFeaturePoint(
                    timestamp="2026-03-31T00:00:00+00:00",
                    alpha_price_tao=11.4,
                    tao_in_pool=7_900.0,
                    emission_per_block_tao=0.065,
                    active_ratio=0.30,
                    participation_breadth=0.17,
                    validator_participation=0.19,
                    incentive_distribution_quality=0.37,
                    market_structure_floor=0.28,
                ),
            ],
        )
    )

    assert retained.raw["post_incentive_retention"] > 0
    assert retained.raw["post_incentive_retention"] > subsidized.raw["post_incentive_retention"]


def test_zero_positive_only_mispricing_features_do_not_score_as_positive():
    inert_bundle, active_bundle, strong_bundle = normalize_features(
        [
            compute_raw_features(
                _snapshot(
                    active_neurons_7d=5,
                    unique_coldkeys=3,
                    n_validators=3,
                    tao_in_pool=20_000.0,
                    alpha_in_pool=5_000.0,
                    alpha_price_tao=10.0,
                    emission_per_block_tao=0.04,
                    history=[
                        HistoricalFeaturePoint(
                            timestamp="2026-03-29T00:00:00+00:00",
                            alpha_price_tao=10.0,
                            tao_in_pool=20_000.0,
                            emission_per_block_tao=0.04,
                            active_ratio=0.50,
                            participation_breadth=0.30,
                            validator_participation=0.30,
                            incentive_distribution_quality=0.45,
                            market_structure_floor=0.50,
                        ),
                        HistoricalFeaturePoint(
                            timestamp="2026-03-30T00:00:00+00:00",
                            alpha_price_tao=10.0,
                            tao_in_pool=20_000.0,
                            emission_per_block_tao=0.04,
                            active_ratio=0.50,
                            participation_breadth=0.30,
                            validator_participation=0.30,
                            incentive_distribution_quality=0.45,
                            market_structure_floor=0.50,
                        ),
                        HistoricalFeaturePoint(
                            timestamp="2026-03-31T00:00:00+00:00",
                            alpha_price_tao=10.0,
                            tao_in_pool=20_000.0,
                            emission_per_block_tao=0.04,
                            active_ratio=0.50,
                            participation_breadth=0.30,
                            validator_participation=0.30,
                            incentive_distribution_quality=0.45,
                            market_structure_floor=0.50,
                        ),
                    ],
                )
            ),
            compute_raw_features(
                _snapshot(
                    active_neurons_7d=7,
                    unique_coldkeys=8,
                    n_validators=7,
                    tao_in_pool=32_000.0,
                    alpha_in_pool=8_000.0,
                    alpha_price_tao=10.1,
                    emission_per_block_tao=0.04,
                    history=[
                        HistoricalFeaturePoint(
                            timestamp="2026-03-29T00:00:00+00:00",
                            alpha_price_tao=10.0,
                            tao_in_pool=26_000.0,
                            emission_per_block_tao=0.046,
                            active_ratio=0.42,
                            participation_breadth=0.22,
                            validator_participation=0.24,
                            incentive_distribution_quality=0.41,
                            market_structure_floor=0.36,
                        ),
                        HistoricalFeaturePoint(
                            timestamp="2026-03-30T00:00:00+00:00",
                            alpha_price_tao=10.0,
                            tao_in_pool=28_000.0,
                            emission_per_block_tao=0.043,
                            active_ratio=0.48,
                            participation_breadth=0.28,
                            validator_participation=0.32,
                            incentive_distribution_quality=0.45,
                            market_structure_floor=0.44,
                        ),
                        HistoricalFeaturePoint(
                            timestamp="2026-03-31T00:00:00+00:00",
                            alpha_price_tao=10.0,
                            tao_in_pool=30_000.0,
                            emission_per_block_tao=0.041,
                            active_ratio=0.54,
                            participation_breadth=0.35,
                            validator_participation=0.40,
                            incentive_distribution_quality=0.50,
                            market_structure_floor=0.53,
                        ),
                    ],
                )
            ),
            compute_raw_features(
                _snapshot(
                    active_neurons_7d=8,
                    unique_coldkeys=9,
                    n_validators=8,
                    tao_in_pool=42_000.0,
                    alpha_in_pool=10_500.0,
                    alpha_price_tao=10.05,
                    emission_per_block_tao=0.038,
                    history=[
                        HistoricalFeaturePoint(
                            timestamp="2026-03-29T00:00:00+00:00",
                            alpha_price_tao=10.0,
                            tao_in_pool=28_000.0,
                            emission_per_block_tao=0.047,
                            active_ratio=0.38,
                            participation_breadth=0.18,
                            validator_participation=0.22,
                            incentive_distribution_quality=0.39,
                            market_structure_floor=0.31,
                        ),
                        HistoricalFeaturePoint(
                            timestamp="2026-03-30T00:00:00+00:00",
                            alpha_price_tao=10.0,
                            tao_in_pool=32_000.0,
                            emission_per_block_tao=0.043,
                            active_ratio=0.46,
                            participation_breadth=0.25,
                            validator_participation=0.30,
                            incentive_distribution_quality=0.44,
                            market_structure_floor=0.40,
                        ),
                        HistoricalFeaturePoint(
                            timestamp="2026-03-31T00:00:00+00:00",
                            alpha_price_tao=10.0,
                            tao_in_pool=36_000.0,
                            emission_per_block_tao=0.040,
                            active_ratio=0.54,
                            participation_breadth=0.34,
                            validator_participation=0.40,
                            incentive_distribution_quality=0.50,
                            market_structure_floor=0.50,
                        ),
                    ],
                )
            ),
        ]
    )

    assert inert_bundle.raw["reserve_growth_without_price"] == 0.0
    assert inert_bundle.metrics["reserve_growth_without_price"].normalized == 0.0
    assert active_bundle.raw["reserve_growth_without_price"] > 0.0
    assert strong_bundle.raw["reserve_growth_without_price"] > active_bundle.raw["reserve_growth_without_price"]
    assert active_bundle.metrics["reserve_growth_without_price"].normalized >= inert_bundle.metrics["reserve_growth_without_price"].normalized
    assert strong_bundle.metrics["reserve_growth_without_price"].normalized > inert_bundle.metrics["reserve_growth_without_price"].normalized


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


def test_structural_concentration_is_discounted_for_liquid_broad_flagships():
    flagship = compute_raw_features(
        _snapshot(
            n_total=64,
            yuma_neurons=64,
            active_neurons_7d=20,
            unique_coldkeys=24,
            n_validators=8,
            tao_in_pool=180_000.0,
            alpha_in_pool=18_000.0,
            top3_stake_fraction=0.94,
            validator_stakes=[92.0, 4.0, 2.0, 1.0, 0.5, 0.3, 0.1, 0.1],
            incentive_scores=[95.0, 2.0, 1.2, 0.8, 0.5, 0.3, 0.1],
        )
    )
    micro = compute_raw_features(
        _snapshot(
            n_total=10,
            yuma_neurons=10,
            active_neurons_7d=2,
            unique_coldkeys=2,
            n_validators=2,
            tao_in_pool=700.0,
            alpha_in_pool=6.0,
            top3_stake_fraction=1.0,
            validator_stakes=[99.0, 1.0],
            incentive_scores=[99.0, 1.0],
        )
    )

    assert flagship.raw["validator_dominance"] < flagship.raw["validator_dominance_raw"]
    assert flagship.raw["incentive_concentration"] < flagship.raw["incentive_concentration_raw"]
    assert flagship.raw["structural_concentration_risk"] < micro.raw["structural_concentration_risk"]
    assert flagship.raw["incentive_distribution_quality"] > flagship.raw["incentive_distribution_quality_raw"]


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


def test_mispricing_surprise_block_rewards_underreaction_and_discounts_overreaction():
    underreacting = compute_raw_features(
        _snapshot(
            active_neurons_7d=7,
            unique_coldkeys=8,
            n_validators=6,
            tao_in_pool=42_000.0,
            alpha_in_pool=8_500.0,
            alpha_price_tao=10.1,
            history=[
                HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=10.0, tao_in_pool=34_000.0, active_ratio=0.48, fundamental_quality=0.42),
                HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=10.0, tao_in_pool=38_000.0, active_ratio=0.56, fundamental_quality=0.52),
                HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=10.0, tao_in_pool=40_000.0, active_ratio=0.64, fundamental_quality=0.64),
            ],
        )
    )
    overreacting = compute_raw_features(
        _snapshot(
            active_neurons_7d=3,
            unique_coldkeys=3,
            n_validators=2,
            tao_in_pool=8_000.0,
            alpha_in_pool=120.0,
            alpha_price_tao=14.0,
            top3_stake_fraction=0.82,
            incentive_scores=[0.85, 0.15],
            history=[
                HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=8.0, tao_in_pool=7_900.0, active_ratio=0.30, fundamental_quality=0.41),
                HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=10.5, tao_in_pool=8_000.0, active_ratio=0.29, fundamental_quality=0.40),
                HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=12.5, tao_in_pool=8_050.0, active_ratio=0.28, fundamental_quality=0.39),
            ],
        )
    )

    assert underreacting.raw["underreaction_score"] > overreacting.raw["underreaction_score"]
    assert overreacting.raw["overreaction_score"] > underreacting.raw["overreaction_score"]


def test_confidence_adjusted_mispricing_discounted_by_signal_fabrication_risk():
    robust_bundle, noisy_bundle = normalize_features(
        [
            compute_raw_features(
                _snapshot(
                    active_neurons_7d=7,
                    unique_coldkeys=8,
                    n_validators=6,
                    tao_in_pool=35_000.0,
                    alpha_in_pool=9_000.0,
                    alpha_price_tao=10.2,
                    history=[
                        HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=10.0, tao_in_pool=30_000.0, active_ratio=0.45, fundamental_quality=0.46),
                        HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=10.1, tao_in_pool=32_000.0, active_ratio=0.52, fundamental_quality=0.54),
                        HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=10.1, tao_in_pool=34_000.0, active_ratio=0.60, fundamental_quality=0.61),
                    ],
                )
            ),
            compute_raw_features(
                _snapshot(
                    active_neurons_7d=2,
                    unique_coldkeys=2,
                    n_validators=2,
                    tao_in_pool=5_200.0,
                    alpha_in_pool=75.0,
                    alpha_price_tao=12.4,
                    top3_stake_fraction=0.86,
                    incentive_scores=[0.94, 0.06],
                    history=[
                        HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=7.0, tao_in_pool=5_000.0, active_ratio=0.22, fundamental_quality=0.41),
                        HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=9.5, tao_in_pool=5_050.0, active_ratio=0.21, fundamental_quality=0.40),
                        HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=11.6, tao_in_pool=5_100.0, active_ratio=0.20, fundamental_quality=0.39),
                    ],
                )
            ),
        ]
    )

    assert robust_bundle.raw["signal_fabrication_risk"] < noisy_bundle.raw["signal_fabrication_risk"]
    assert robust_bundle.primary_signals.mispricing_signal > noisy_bundle.primary_signals.mispricing_signal
    assert robust_bundle.core_blocks["structural_validity"] > noisy_bundle.core_blocks["structural_validity"]


def test_mispricing_structural_drag_penalizes_extreme_yield_microstructure():
    robust_bundle, hype_bundle = normalize_features(
        [
            compute_raw_features(
                _snapshot(
                    active_neurons_7d=8,
                    unique_coldkeys=9,
                    n_validators=7,
                    tao_in_pool=55_000.0,
                    alpha_in_pool=12_500.0,
                    alpha_price_tao=10.2,
                    emission_per_block_tao=0.025,
                    history=[
                        HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=10.0, tao_in_pool=48_000.0, active_ratio=0.56, fundamental_quality=0.53),
                        HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=10.0, tao_in_pool=51_000.0, active_ratio=0.61, fundamental_quality=0.59),
                        HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=10.1, tao_in_pool=53_000.0, active_ratio=0.66, fundamental_quality=0.65),
                    ],
                )
            ),
            compute_raw_features(
                _snapshot(
                    active_neurons_7d=3,
                    unique_coldkeys=2,
                    n_validators=2,
                    tao_in_pool=750.0,
                    alpha_in_pool=4.5,
                    alpha_price_tao=16.0,
                    emission_per_block_tao=0.04,
                    top3_stake_fraction=0.88,
                    incentive_scores=[0.96, 0.04],
                    history=[
                        HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=10.0, tao_in_pool=650.0, active_ratio=0.22, fundamental_quality=0.38),
                        HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=12.2, tao_in_pool=680.0, active_ratio=0.22, fundamental_quality=0.38),
                        HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=14.5, tao_in_pool=710.0, active_ratio=0.21, fundamental_quality=0.37),
                    ],
                )
            ),
        ]
    )

    assert robust_bundle.core_blocks["structural_validity"] > hype_bundle.core_blocks["structural_validity"]
    assert robust_bundle.primary_signals.mispricing_signal > hype_bundle.primary_signals.mispricing_signal


def test_crowded_repricing_discount_penalizes_crowded_large_names():
    balanced_bundle, crowded_bundle = normalize_features(
        [
            compute_raw_features(
                _snapshot(
                    active_neurons_7d=7,
                    unique_coldkeys=8,
                    n_validators=6,
                    tao_in_pool=52_000.0,
                    alpha_in_pool=12_000.0,
                    alpha_price_tao=10.2,
                    emission_per_block_tao=0.025,
                    top3_stake_fraction=0.42,
                    history=[
                        HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=10.0, tao_in_pool=47_000.0, active_ratio=0.49, fundamental_quality=0.48),
                        HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=10.0, tao_in_pool=49_000.0, active_ratio=0.56, fundamental_quality=0.56),
                        HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=10.1, tao_in_pool=51_000.0, active_ratio=0.62, fundamental_quality=0.63),
                    ],
                )
            ),
            compute_raw_features(
                _snapshot(
                    active_neurons_7d=7,
                    unique_coldkeys=8,
                    n_validators=6,
                    tao_in_pool=210_000.0,
                    alpha_in_pool=18_000.0,
                    alpha_price_tao=16.0,
                    emission_per_block_tao=0.06,
                    top3_stake_fraction=0.78,
                    incentive_scores=[0.92, 0.08],
                    history=[
                        HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=12.0, tao_in_pool=195_000.0, active_ratio=0.50, fundamental_quality=0.50),
                        HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=13.8, tao_in_pool=202_000.0, active_ratio=0.51, fundamental_quality=0.51),
                        HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=15.0, tao_in_pool=207_000.0, active_ratio=0.52, fundamental_quality=0.52),
                    ],
                )
            ),
        ]
    )

    assert balanced_bundle.core_blocks["crowded_structure_watchlist"] < crowded_bundle.core_blocks["crowded_structure_watchlist"]
    assert crowded_bundle.core_blocks["opportunity_underreaction"] >= balanced_bundle.core_blocks["opportunity_underreaction"]
    balanced_discount = balanced_bundle.core_blocks["opportunity_underreaction"] - balanced_bundle.primary_signals.mispricing_signal
    crowded_discount = crowded_bundle.core_blocks["opportunity_underreaction"] - crowded_bundle.primary_signals.mispricing_signal

    assert crowded_discount > balanced_discount


def test_crowded_expectation_saturation_reduces_underreaction_for_popular_large_names():
    balanced = compute_raw_features(
        _snapshot(
            active_neurons_7d=7,
            unique_coldkeys=8,
            n_validators=6,
            tao_in_pool=52_000.0,
            alpha_in_pool=12_000.0,
            alpha_price_tao=10.2,
            emission_per_block_tao=0.025,
            top3_stake_fraction=0.42,
            history=[
                HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=10.0, tao_in_pool=47_000.0, active_ratio=0.49, fundamental_quality=0.48),
                HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=10.0, tao_in_pool=49_000.0, active_ratio=0.56, fundamental_quality=0.56),
                HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=10.1, tao_in_pool=51_000.0, active_ratio=0.62, fundamental_quality=0.63),
            ],
        )
    )
    crowded = compute_raw_features(
        _snapshot(
            active_neurons_7d=7,
            unique_coldkeys=8,
            n_validators=6,
            tao_in_pool=210_000.0,
            alpha_in_pool=18_000.0,
            alpha_price_tao=16.0,
            emission_per_block_tao=0.06,
            top3_stake_fraction=0.78,
            incentive_scores=[0.92, 0.08],
            history=[
                HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=12.0, tao_in_pool=195_000.0, active_ratio=0.50, fundamental_quality=0.50),
                HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=13.8, tao_in_pool=202_000.0, active_ratio=0.51, fundamental_quality=0.51),
                HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=15.0, tao_in_pool=207_000.0, active_ratio=0.52, fundamental_quality=0.52),
            ],
        )
    )

    assert balanced.raw["crowded_expectation_saturation"] < crowded.raw["crowded_expectation_saturation"]
    assert balanced.raw["underreaction_score"] >= balanced.raw["raw_underreaction_score"] * 0.6
    assert crowded.raw["underreaction_score"] < crowded.raw["raw_underreaction_score"]
    if crowded.raw["raw_cohort_implied_fair_value_gap"] > 0:
        assert crowded.raw["cohort_implied_fair_value_gap"] < crowded.raw["raw_cohort_implied_fair_value_gap"]
    else:
        assert crowded.raw["cohort_implied_fair_value_gap"] == crowded.raw["raw_cohort_implied_fair_value_gap"]


def test_signal_confidence_is_discounted_for_reflexive_fragile_structures():
    robust_bundle, crowded_bundle = normalize_features(
        [
            compute_raw_features(
                _snapshot(
                    active_neurons_7d=8,
                    unique_coldkeys=8,
                    n_validators=7,
                    tao_in_pool=48_000.0,
                    alpha_in_pool=11_000.0,
                    alpha_price_tao=10.4,
                    history=[
                        HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=10.0, tao_in_pool=42_000.0, active_ratio=0.56, fundamental_quality=0.55),
                        HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=10.2, tao_in_pool=44_000.0, active_ratio=0.60, fundamental_quality=0.59),
                        HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=10.3, tao_in_pool=46_000.0, active_ratio=0.64, fundamental_quality=0.63),
                    ],
                )
            ),
            compute_raw_features(
                _snapshot(
                    active_neurons_7d=3,
                    unique_coldkeys=2,
                    n_validators=2,
                    tao_in_pool=9_000.0,
                    alpha_in_pool=95.0,
                    alpha_price_tao=14.0,
                    top3_stake_fraction=0.84,
                    incentive_scores=[0.9, 0.1],
                    history=[
                        HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=8.5, tao_in_pool=8_800.0, active_ratio=0.31, fundamental_quality=0.43),
                        HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=11.0, tao_in_pool=8_900.0, active_ratio=0.30, fundamental_quality=0.42),
                        HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=13.1, tao_in_pool=8_950.0, active_ratio=0.29, fundamental_quality=0.41),
                    ],
                )
            ),
        ]
    )

    assert robust_bundle.base_components["crowding_level"] < crowded_bundle.base_components["crowding_level"]
    assert robust_bundle.primary_signals.signal_confidence > crowded_bundle.primary_signals.signal_confidence


def test_evidence_confidence_respects_large_onchain_structure_even_when_freshness_is_thin():
    robust_bundle, reflexive_bundle = normalize_features(
        [
            compute_raw_features(
                _snapshot(
                    active_neurons_7d=8,
                    unique_coldkeys=9,
                    n_validators=7,
                    tao_in_pool=185_000.0,
                    alpha_in_pool=21_000.0,
                    alpha_price_tao=12.8,
                    top3_stake_fraction=0.48,
                    last_update_blocks=[1000, 1000, 0, 0, 0, 0, 0, 0, 0, 0],
                    history=[
                        HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=12.0, tao_in_pool=170_000.0, active_ratio=0.55, fundamental_quality=0.56),
                        HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=12.2, tao_in_pool=176_000.0, active_ratio=0.58, fundamental_quality=0.60),
                        HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=12.4, tao_in_pool=181_000.0, active_ratio=0.61, fundamental_quality=0.64),
                    ],
                )
            ),
            compute_raw_features(
                _snapshot(
                    active_neurons_7d=3,
                    unique_coldkeys=2,
                    n_validators=2,
                    tao_in_pool=5_800.0,
                    alpha_in_pool=95.0,
                    alpha_price_tao=13.1,
                    top3_stake_fraction=0.84,
                    incentive_scores=[0.9, 0.1],
                    last_update_blocks=[1000, 1000, 0, 0, 0, 0, 0, 0, 0, 0],
                    history=[
                        HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=9.5, tao_in_pool=5_300.0, active_ratio=0.27, fundamental_quality=0.42),
                        HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=11.2, tao_in_pool=5_450.0, active_ratio=0.26, fundamental_quality=0.41),
                        HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=12.4, tao_in_pool=5_600.0, active_ratio=0.25, fundamental_quality=0.40),
                    ],
                )
            ),
        ]
    )

    assert robust_bundle.raw["update_freshness"] == reflexive_bundle.raw["update_freshness"]
    assert robust_bundle.raw["proxy_reliance_penalty"] < reflexive_bundle.raw["proxy_reliance_penalty"]
    assert robust_bundle.raw["low_manipulation_signal_share"] > reflexive_bundle.raw["low_manipulation_signal_share"]
    assert robust_bundle.raw["signal_fabrication_risk"] < reflexive_bundle.raw["signal_fabrication_risk"]
    assert robust_bundle.raw["evidence_confidence"] > reflexive_bundle.raw["evidence_confidence"]


def test_missing_consensus_signals_reduce_evidence_confidence():
    with_consensus = normalize_features(
        [
            compute_raw_features(
                _snapshot(
                    validator_weight_matrix=[
                        [0.4, 0.3, 0.2, 0.1],
                        [0.3, 0.3, 0.2, 0.2],
                        [0.35, 0.25, 0.2, 0.2],
                    ],
                    validator_bond_matrix=[
                        [0.5, 0.3, 0.2],
                        [0.45, 0.35, 0.2],
                        [0.4, 0.4, 0.2],
                    ],
                    history=[
                        HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=10.0, tao_in_pool=900.0, active_ratio=0.45, fundamental_quality=0.50),
                        HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=10.1, tao_in_pool=940.0, active_ratio=0.47, fundamental_quality=0.53),
                        HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=10.2, tao_in_pool=980.0, active_ratio=0.49, fundamental_quality=0.56),
                    ],
                )
            )
        ]
    )[0]
    without_consensus = normalize_features(
        [
            compute_raw_features(
                _snapshot(
                    validator_weight_matrix=[],
                    validator_bond_matrix=[],
                    history=[
                        HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=10.0, tao_in_pool=900.0, active_ratio=0.45, fundamental_quality=0.50),
                        HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=10.1, tao_in_pool=940.0, active_ratio=0.47, fundamental_quality=0.53),
                        HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=10.2, tao_in_pool=980.0, active_ratio=0.49, fundamental_quality=0.56),
                    ],
                )
            )
        ]
    )[0]

    assert with_consensus.raw["consensus_signal_gap"] < without_consensus.raw["consensus_signal_gap"]
    assert with_consensus.raw["evidence_confidence"] > without_consensus.raw["evidence_confidence"]


def test_missing_consensus_and_external_evidence_cap_confidence_even_for_large_onchain_names():
    supported_bundle, unsupported_bundle = normalize_features(
        [
            compute_raw_features(
                _snapshot(
                    active_neurons_7d=8,
                    unique_coldkeys=9,
                    n_validators=7,
                    tao_in_pool=180_000.0,
                    alpha_in_pool=20_000.0,
                    alpha_price_tao=12.4,
                    validator_weight_matrix=[
                        [0.4, 0.3, 0.2, 0.1],
                        [0.3, 0.3, 0.2, 0.2],
                        [0.35, 0.25, 0.2, 0.2],
                    ],
                    validator_bond_matrix=[
                        [0.5, 0.3, 0.2],
                        [0.45, 0.35, 0.2],
                        [0.4, 0.4, 0.2],
                    ],
                    github=None,
                    history=[
                        HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=12.0, tao_in_pool=168_000.0, active_ratio=0.56, fundamental_quality=0.57),
                        HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=12.1, tao_in_pool=172_000.0, active_ratio=0.59, fundamental_quality=0.60),
                        HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=12.2, tao_in_pool=176_000.0, active_ratio=0.62, fundamental_quality=0.63),
                    ],
                )
            ),
            compute_raw_features(
                _snapshot(
                    active_neurons_7d=8,
                    unique_coldkeys=9,
                    n_validators=7,
                    tao_in_pool=180_000.0,
                    alpha_in_pool=20_000.0,
                    alpha_price_tao=12.4,
                    validator_weight_matrix=[],
                    validator_bond_matrix=[],
                    github=None,
                    history=[
                        HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=12.0, tao_in_pool=168_000.0, active_ratio=0.56, fundamental_quality=0.57),
                        HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=12.1, tao_in_pool=172_000.0, active_ratio=0.59, fundamental_quality=0.60),
                        HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=12.2, tao_in_pool=176_000.0, active_ratio=0.62, fundamental_quality=0.63),
                    ],
                )
            ),
        ]
    )

    assert unsupported_bundle.raw["evidence_confidence"] <= unsupported_bundle.core_blocks["evidence_confidence"]
    assert supported_bundle.base_components["data_confidence"] > unsupported_bundle.base_components["data_confidence"]
    assert supported_bundle.base_components["thesis_confidence"] > unsupported_bundle.base_components["thesis_confidence"]
    assert supported_bundle.primary_signals.signal_confidence > unsupported_bundle.primary_signals.signal_confidence


def test_crowded_structure_penalty_raises_fragility_and_dampens_confidence():
    balanced_bundle, crowded_bundle = normalize_features(
        [
            compute_raw_features(
                _snapshot(
                    active_neurons_7d=8,
                    unique_coldkeys=8,
                    n_validators=7,
                    tao_in_pool=85_000.0,
                    alpha_in_pool=14_000.0,
                    alpha_price_tao=10.3,
                    top3_stake_fraction=0.44,
                    emission_per_block_tao=0.026,
                    validator_weight_matrix=[
                        [0.4, 0.3, 0.2, 0.1],
                        [0.3, 0.3, 0.2, 0.2],
                        [0.35, 0.25, 0.2, 0.2],
                    ],
                    validator_bond_matrix=[
                        [0.5, 0.3, 0.2],
                        [0.45, 0.35, 0.2],
                        [0.4, 0.4, 0.2],
                    ],
                    history=[
                        HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=10.0, tao_in_pool=78_000.0, active_ratio=0.54, fundamental_quality=0.53),
                        HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=10.1, tao_in_pool=81_000.0, active_ratio=0.57, fundamental_quality=0.57),
                        HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=10.2, tao_in_pool=83_000.0, active_ratio=0.60, fundamental_quality=0.61),
                    ],
                )
            ),
            compute_raw_features(
                _snapshot(
                    active_neurons_7d=8,
                    unique_coldkeys=8,
                    n_validators=7,
                    tao_in_pool=210_000.0,
                    alpha_in_pool=18_000.0,
                    alpha_price_tao=16.0,
                    top3_stake_fraction=0.78,
                    incentive_scores=[0.92, 0.08],
                    emission_per_block_tao=0.06,
                    validator_weight_matrix=[
                        [0.65, 0.2, 0.1, 0.05],
                        [0.62, 0.2, 0.1, 0.08],
                        [0.7, 0.15, 0.1, 0.05],
                    ],
                    validator_bond_matrix=[
                        [0.72, 0.18, 0.1],
                        [0.7, 0.2, 0.1],
                        [0.74, 0.16, 0.1],
                    ],
                    history=[
                        HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=12.0, tao_in_pool=195_000.0, active_ratio=0.50, fundamental_quality=0.50),
                        HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=13.8, tao_in_pool=202_000.0, active_ratio=0.51, fundamental_quality=0.51),
                        HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=15.0, tao_in_pool=207_000.0, active_ratio=0.52, fundamental_quality=0.52),
                    ],
                )
            ),
        ]
    )

    assert balanced_bundle.core_blocks["crowded_structure_watchlist"] < crowded_bundle.core_blocks["crowded_structure_watchlist"]
    assert balanced_bundle.primary_signals.fragility_risk < crowded_bundle.primary_signals.fragility_risk
    assert balanced_bundle.primary_signals.signal_confidence > crowded_bundle.primary_signals.signal_confidence


def test_signal_confidence_uses_structural_ceiling_for_crowded_yield_setups():
    robust_bundle, crowded_bundle = normalize_features(
        [
            compute_raw_features(
                _snapshot(
                    active_neurons_7d=8,
                    unique_coldkeys=9,
                    n_validators=7,
                    tao_in_pool=80_000.0,
                    alpha_in_pool=15_000.0,
                    alpha_price_tao=10.5,
                    emission_per_block_tao=0.03,
                    history=[
                        HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=10.0, tao_in_pool=72_000.0, active_ratio=0.58, fundamental_quality=0.56),
                        HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=10.2, tao_in_pool=75_000.0, active_ratio=0.61, fundamental_quality=0.60),
                        HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=10.3, tao_in_pool=78_000.0, active_ratio=0.65, fundamental_quality=0.64),
                    ],
                )
            ),
            compute_raw_features(
                _snapshot(
                    active_neurons_7d=6,
                    unique_coldkeys=4,
                    n_validators=3,
                    tao_in_pool=18_000.0,
                    alpha_in_pool=350.0,
                    alpha_price_tao=15.2,
                    emission_per_block_tao=0.06,
                    top3_stake_fraction=0.72,
                    incentive_scores=[0.82, 0.12, 0.06],
                    history=[
                        HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=10.8, tao_in_pool=17_000.0, active_ratio=0.34, fundamental_quality=0.44),
                        HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=12.8, tao_in_pool=17_400.0, active_ratio=0.33, fundamental_quality=0.44),
                        HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=14.6, tao_in_pool=17_800.0, active_ratio=0.32, fundamental_quality=0.43),
                    ],
                )
            ),
        ]
    )

    assert robust_bundle.core_blocks["structural_validity"] > crowded_bundle.core_blocks["structural_validity"]
    assert crowded_bundle.primary_signals.signal_confidence <= crowded_bundle.raw["evidence_confidence"]
    assert robust_bundle.primary_signals.signal_confidence > crowded_bundle.primary_signals.signal_confidence


def test_signal_confidence_is_bounded_by_lower_of_evidence_and_thesis_confidence():
    robust_bundle, structurally_weak_bundle = normalize_features(
        [
            compute_raw_features(
                _snapshot(
                    active_neurons_7d=8,
                    unique_coldkeys=9,
                    n_validators=7,
                    tao_in_pool=70_000.0,
                    alpha_in_pool=12_500.0,
                    alpha_price_tao=10.4,
                    emission_per_block_tao=0.03,
                    history=[
                        HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=10.0, tao_in_pool=62_000.0, active_ratio=0.57, fundamental_quality=0.55),
                        HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=10.1, tao_in_pool=65_000.0, active_ratio=0.60, fundamental_quality=0.58),
                        HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=10.2, tao_in_pool=68_000.0, active_ratio=0.63, fundamental_quality=0.62),
                    ],
                )
            ),
            compute_raw_features(
                _snapshot(
                    active_neurons_7d=7,
                    unique_coldkeys=7,
                    n_validators=6,
                    tao_in_pool=22_000.0,
                    alpha_in_pool=280.0,
                    alpha_price_tao=14.2,
                    emission_per_block_tao=0.055,
                    top3_stake_fraction=0.75,
                    incentive_scores=[0.86, 0.08, 0.06],
                    history=[
                        HistoricalFeaturePoint(timestamp="2026-03-29T00:00:00+00:00", alpha_price_tao=11.5, tao_in_pool=20_800.0, active_ratio=0.40, fundamental_quality=0.49),
                        HistoricalFeaturePoint(timestamp="2026-03-30T00:00:00+00:00", alpha_price_tao=12.8, tao_in_pool=21_200.0, active_ratio=0.39, fundamental_quality=0.48),
                        HistoricalFeaturePoint(timestamp="2026-03-31T00:00:00+00:00", alpha_price_tao=13.8, tao_in_pool=21_700.0, active_ratio=0.38, fundamental_quality=0.47),
                    ],
                )
            ),
        ]
    )

    assert robust_bundle.primary_signals.signal_confidence <= robust_bundle.raw["evidence_confidence"]
    assert robust_bundle.primary_signals.signal_confidence <= robust_bundle.base_components["thesis_confidence"]
    assert structurally_weak_bundle.primary_signals.signal_confidence <= structurally_weak_bundle.raw["evidence_confidence"]
    assert structurally_weak_bundle.primary_signals.signal_confidence <= structurally_weak_bundle.base_components["thesis_confidence"]
    assert robust_bundle.primary_signals.signal_confidence > structurally_weak_bundle.primary_signals.signal_confidence


def test_removed_legacy_compatibility_fields_are_not_emitted_from_v2_bundle():
    bundle = normalize_features([compute_raw_features(_snapshot())])[0]

    removed_fields = {
        "base_mispricing_signal",
        "evidence_confidence_ceiling",
        "reflexive_confidence_drag",
        "structural_confidence_drag",
        "mispricing_structural_drag",
        "crowded_repricing_discount",
        "confidence_adjusted_mispricing",
        "confidence_adjusted_thesis_strength",
        "base_signal_confidence",
        "crowded_structure_penalty",
        "quality_resolution_bonus",
        "quality_resolution_drag",
    }

    assert removed_fields.isdisjoint(bundle.raw)

