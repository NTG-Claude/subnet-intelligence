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
    assert robust_bundle.raw["mispricing_structural_drag"] < noisy_bundle.raw["mispricing_structural_drag"]


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

    assert robust_bundle.raw["mispricing_structural_drag"] < hype_bundle.raw["mispricing_structural_drag"]
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

    assert balanced_bundle.raw["crowded_repricing_discount"] < crowded_bundle.raw["crowded_repricing_discount"]
    assert crowded_bundle.raw["base_mispricing_signal"] > balanced_bundle.raw["base_mispricing_signal"]
    balanced_discount = balanced_bundle.raw["base_mispricing_signal"] - balanced_bundle.primary_signals.mispricing_signal
    crowded_discount = crowded_bundle.raw["base_mispricing_signal"] - crowded_bundle.primary_signals.mispricing_signal

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

    assert robust_bundle.raw["reflexive_confidence_drag"] < crowded_bundle.raw["reflexive_confidence_drag"]
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

    assert robust_bundle.raw["structural_confidence_drag"] < crowded_bundle.raw["structural_confidence_drag"]
    assert crowded_bundle.primary_signals.signal_confidence <= crowded_bundle.raw["confidence_structural_ceiling"]
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
    assert robust_bundle.primary_signals.signal_confidence <= robust_bundle.raw["adjusted_thesis_confidence"]
    assert structurally_weak_bundle.primary_signals.signal_confidence <= structurally_weak_bundle.raw["evidence_confidence"]
    assert structurally_weak_bundle.primary_signals.signal_confidence <= structurally_weak_bundle.raw["adjusted_thesis_confidence"]
    assert robust_bundle.primary_signals.signal_confidence > structurally_weak_bundle.primary_signals.signal_confidence

