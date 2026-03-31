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


def evaluate_hard_rules(snapshot: RawSubnetSnapshot, bundle: FeatureBundle) -> HardRuleResult:
    activated: list[str] = []
    intrinsic_cap = None
    economic_cap = None
    total_cap = None
    force_negative_label = False
    active_ratio = bundle.raw.get("active_ratio") or 0.0
    max_slippage = max(bundle.raw.get("slippage_10_tao") or 0.0, bundle.raw.get("slippage_50_tao") or 0.0)
    concentration = max(bundle.raw.get("validator_dominance") or 0.0, bundle.raw.get("incentive_concentration") or 0.0)
    consensus_hollow = (
        (bundle.raw.get("validator_weight_entropy") or 0.0) > 0.92
        and (bundle.raw.get("cross_validator_disagreement") or 0.0) < 0.08
        and (bundle.raw.get("meaningful_discrimination") or 0.0) < 0.12
    )

    if snapshot.yuma_neurons == 0 or active_ratio < 0.10:
        activated.append("inactive_subnet_blocks_positive_label")
        total_cap = 0.35
        force_negative_label = True

    if snapshot.tao_in_pool < 25 or max_slippage > 0.45:
        activated.append("thin_liquidity_caps_economic_sustainability")
        economic_cap = 0.35 if economic_cap is None else min(economic_cap, 0.35)

    if concentration > 0.60:
        activated.append("concentration_caps_intrinsic_quality")
        intrinsic_cap = 0.45 if intrinsic_cap is None else min(intrinsic_cap, 0.45)

    if consensus_hollow:
        activated.append("uninformative_consensus_caps_consensus_component")
        intrinsic_cap = 0.50 if intrinsic_cap is None else min(intrinsic_cap, 0.50)

    return HardRuleResult(
        activated=activated,
        intrinsic_cap=intrinsic_cap,
        economic_cap=economic_cap,
        total_cap=total_cap,
        force_negative_label=force_negative_label,
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
