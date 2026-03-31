from collectors.models import RawSubnetSnapshot
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

