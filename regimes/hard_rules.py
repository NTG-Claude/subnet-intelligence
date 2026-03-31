from dataclasses import dataclass

from collectors.models import RawSubnetSnapshot
from features.types import AxisScores, FeatureBundle


@dataclass
class HardRuleResult:
    activated: list[str]
    intrinsic_cap: float | None = None
    economic_cap: float | None = None
    total_cap: float | None = None
    force_negative_label: bool = False
    force_label: str | None = None


def evaluate_hard_rules(snapshot: RawSubnetSnapshot, bundle: FeatureBundle) -> HardRuleResult:
    activated: list[str] = []
    intrinsic_cap = None
    economic_cap = None
    total_cap = None
    force_negative_label = False
    force_label = None
    active_ratio = bundle.raw.get("active_ratio") or 0.0
    max_slippage = max(bundle.raw.get("slippage_10_tao") or 0.0, bundle.raw.get("slippage_50_tao") or 0.0)
    concentration = max(bundle.raw.get("validator_dominance") or 0.0, bundle.raw.get("incentive_concentration") or 0.0)
    update_freshness = bundle.raw.get("update_freshness") or 0.0
    participation = bundle.raw.get("participation_breadth") or 0.0
    pool_depth = snapshot.tao_in_pool or 0.0
    staking_apy = 0.0
    if pool_depth > 0:
        staking_apy = max(0.0, snapshot.emission_per_block_tao * 7200 * 365 / pool_depth * 100)
    consensus_hollow = (
        (bundle.raw.get("validator_weight_entropy") or 0.0) > 0.92
        and (bundle.raw.get("cross_validator_disagreement") or 0.0) < 0.08
        and (bundle.raw.get("meaningful_discrimination") or 0.0) < 0.12
    )

    structurally_inactive = (
        snapshot.yuma_neurons == 0
        or (
            active_ratio < 0.03
            and update_freshness < 0.03
            and participation < 0.35
            and pool_depth < 5000
        )
    )
    if structurally_inactive:
        activated.append("inactive_subnet_blocks_positive_label")
        total_cap = 0.24 if total_cap is None else min(total_cap, 0.24)
        force_negative_label = True
        force_label = "Dereg Candidate"

    if pool_depth < 100 or max_slippage > 0.35:
        activated.append("thin_liquidity_caps_economic_sustainability")
        economic_cap = 0.08 if economic_cap is None else min(economic_cap, 0.08)
        total_cap = 0.16 if total_cap is None else min(total_cap, 0.16)
        force_negative_label = True
        force_label = force_label or "Overrewarded Structure"

    if pool_depth < 250 and staking_apy > 150:
        activated.append("micro_pool_apy_caps_total_score")
        economic_cap = 0.05 if economic_cap is None else min(economic_cap, 0.05)
        total_cap = 0.12 if total_cap is None else min(total_cap, 0.12)
        force_negative_label = True
        force_label = force_label or "Overrewarded Structure"

    if not snapshot.registration_allowed and snapshot.min_burn <= 0 and snapshot.max_burn <= 0 and snapshot.difficulty <= 0:
        activated.append("registration_closed_without_burn_or_pow_penalty")
        total_cap = 0.32 if total_cap is None else min(total_cap, 0.32)
        force_negative_label = True
        force_label = "Dereg Candidate"

    if concentration > 0.60:
        activated.append("concentration_caps_intrinsic_quality")
        intrinsic_cap = 0.35 if intrinsic_cap is None else min(intrinsic_cap, 0.35)

    if consensus_hollow:
        activated.append("uninformative_consensus_caps_consensus_component")
        intrinsic_cap = 0.50 if intrinsic_cap is None else min(intrinsic_cap, 0.50)
        force_label = force_label or "Consensus Hollow"

    if snapshot.immunity_period <= 0 and (bundle.raw.get("dereg_risk_proxy") or 0.0) > 0.55:
        activated.append("post_immunity_high_dereg_risk_penalty")
        total_cap = 0.24 if total_cap is None else min(total_cap, 0.24)
        force_negative_label = True
        force_label = force_label or "Dereg Candidate"

    return HardRuleResult(
        activated=activated,
        intrinsic_cap=intrinsic_cap,
        economic_cap=economic_cap,
        total_cap=total_cap,
        force_negative_label=force_negative_label,
        force_label=force_label,
    )


def apply_rule_caps(axes: AxisScores, rules: HardRuleResult) -> AxisScores:
    intrinsic = min(axes.intrinsic_quality, rules.intrinsic_cap) if rules.intrinsic_cap is not None else axes.intrinsic_quality
    economic = min(axes.economic_sustainability, rules.economic_cap) if rules.economic_cap is not None else axes.economic_sustainability
    return AxisScores(
        intrinsic_quality=intrinsic,
        economic_sustainability=economic,
        reflexivity=axes.reflexivity,
        stress_robustness=axes.stress_robustness,
        opportunity_gap=axes.opportunity_gap,
    )
