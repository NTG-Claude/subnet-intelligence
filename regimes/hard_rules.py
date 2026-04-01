from dataclasses import dataclass

from collectors.models import RawSubnetSnapshot
from features.types import FeatureBundle, PrimarySignals


@dataclass
class HardRuleResult:
    activated: list[str]
    quality_cap: float | None = None
    mispricing_cap: float | None = None
    confidence_cap: float | None = None
    fragility_floor: float | None = None
    legacy_score_cap: float | None = None
    total_cap: float | None = None
    force_negative_label: bool = False
    force_label: str | None = None

    def __post_init__(self) -> None:
        if self.legacy_score_cap is None and self.total_cap is not None:
            self.legacy_score_cap = self.total_cap
        if self.total_cap is None and self.legacy_score_cap is not None:
            self.total_cap = self.legacy_score_cap


def evaluate_hard_rules(snapshot: RawSubnetSnapshot, bundle: FeatureBundle) -> HardRuleResult:
    activated: list[str] = []
    quality_cap = None
    mispricing_cap = None
    confidence_cap = None
    fragility_floor = None
    legacy_score_cap = None
    force_negative_label = False
    force_label = None

    active_ratio = bundle.raw.get("active_ratio") or 0.0
    max_slippage = max(bundle.raw.get("slippage_10_tao") or 0.0, bundle.raw.get("slippage_50_tao") or 0.0)
    concentration = max(bundle.raw.get("validator_dominance") or 0.0, bundle.raw.get("incentive_concentration") or 0.0)
    update_freshness = bundle.raw.get("update_freshness") or 0.0
    participation = bundle.raw.get("participation_breadth") or 0.0
    concentration_delta = bundle.raw.get("concentration_delta")
    pool_depth = snapshot.tao_in_pool or 0.0
    market_relevance = bundle.raw.get("market_relevance_proxy") or 0.0
    market_structure_floor = bundle.raw.get("market_structure_floor") or 0.0
    confidence_inputs = bundle.raw.get("data_coverage") or 0.0
    proxy_reliance = bundle.raw.get("proxy_reliance_penalty") or 0.0
    thesis_coherence = bundle.raw.get("confidence_thesis_coherence") or 0.0
    signal_fabrication_risk = bundle.raw.get("signal_fabrication_risk") or 0.0
    low_evidence_high_conviction = bundle.raw.get("low_evidence_high_conviction") or 0.0
    underreaction_score = bundle.raw.get("underreaction_score") or 0.0
    crowding_proxy = bundle.raw.get("crowding_proxy") or 0.0
    overreaction_score = bundle.raw.get("overreaction_score") or 0.0
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
        quality_cap = 0.18 if quality_cap is None else min(quality_cap, 0.18)
        mispricing_cap = 0.12 if mispricing_cap is None else min(mispricing_cap, 0.12)
        confidence_cap = 0.40 if confidence_cap is None else min(confidence_cap, 0.40)
        fragility_floor = 0.85 if fragility_floor is None else max(fragility_floor, 0.85)
        legacy_score_cap = 0.24 if legacy_score_cap is None else min(legacy_score_cap, 0.24)
        force_negative_label = True
        force_label = "Dereg Candidate"

    if pool_depth < 100 or max_slippage > 0.35:
        activated.append("thin_liquidity_caps_fragility")
        mispricing_cap = 0.22 if mispricing_cap is None else min(mispricing_cap, 0.22)
        confidence_cap = 0.55 if confidence_cap is None else min(confidence_cap, 0.55)
        fragility_floor = 0.82 if fragility_floor is None else max(fragility_floor, 0.82)
        legacy_score_cap = 0.16 if legacy_score_cap is None else min(legacy_score_cap, 0.16)
        force_negative_label = True
        force_label = force_label or "Overrewarded Structure"

    if pool_depth < 250 and staking_apy > 150:
        activated.append("micro_pool_apy_caps_total_score")
        quality_cap = 0.28 if quality_cap is None else min(quality_cap, 0.28)
        mispricing_cap = 0.10 if mispricing_cap is None else min(mispricing_cap, 0.10)
        confidence_cap = 0.42 if confidence_cap is None else min(confidence_cap, 0.42)
        fragility_floor = 0.88 if fragility_floor is None else max(fragility_floor, 0.88)
        legacy_score_cap = 0.12 if legacy_score_cap is None else min(legacy_score_cap, 0.12)
        force_negative_label = True
        force_label = force_label or "Overrewarded Structure"

    if pool_depth < 7_500 and staking_apy > 150:
        activated.append("small_pool_yield_intensity_caps_confidence")
        confidence_cap = 0.46 if confidence_cap is None else min(confidence_cap, 0.46)
        mispricing_cap = 0.42 if mispricing_cap is None else min(mispricing_cap, 0.42)
        fragility_floor = 0.68 if fragility_floor is None else max(fragility_floor, 0.68)

    if pool_depth < 2_500 and staking_apy > 180:
        activated.append("extreme_yield_small_pool_caps_mispricing")
        mispricing_cap = 0.18 if mispricing_cap is None else min(mispricing_cap, 0.18)
        confidence_cap = 0.42 if confidence_cap is None else min(confidence_cap, 0.42)
        fragility_floor = 0.76 if fragility_floor is None else max(fragility_floor, 0.76)

    if (
        pool_depth < 10_000
        and staking_apy > 110
        and (
            market_structure_floor < 0.58
            or max_slippage > 0.05
            or concentration > 0.75
        )
    ):
        activated.append("fragile_repricing_blocks_top_mispricing")
        mispricing_cap = 0.26 if mispricing_cap is None else min(mispricing_cap, 0.26)
        confidence_cap = 0.48 if confidence_cap is None else min(confidence_cap, 0.48)
        fragility_floor = 0.72 if fragility_floor is None else max(fragility_floor, 0.72)

    elevated_yield_confidence_breach = (
        pool_depth < 10_000
        and staking_apy > 100
        and (
            market_structure_floor < 0.62
            or concentration > 0.78
            or max_slippage > 0.04
        )
    )
    if elevated_yield_confidence_breach:
        activated.append("elevated_yield_small_pool_caps_confidence")
        confidence_cap = 0.52 if confidence_cap is None else min(confidence_cap, 0.52)
        fragility_floor = 0.66 if fragility_floor is None else max(fragility_floor, 0.66)

    severe_market_structure_breach = (
        pool_depth < 1_500
        and staking_apy > 250
        and market_structure_floor < 0.45
    )
    moderate_market_structure_breach = (
        pool_depth < 7_500
        and (
            market_structure_floor < 0.42
            or max_slippage > 0.12
            or staking_apy > 220
        )
    )

    if severe_market_structure_breach:
        activated.append("market_structure_floor_blocks_top_rank")
        quality_cap = 0.34 if quality_cap is None else min(quality_cap, 0.34)
        mispricing_cap = 0.24 if mispricing_cap is None else min(mispricing_cap, 0.24)
        confidence_cap = 0.48 if confidence_cap is None else min(confidence_cap, 0.48)
        fragility_floor = 0.78 if fragility_floor is None else max(fragility_floor, 0.78)
        legacy_score_cap = 0.34 if legacy_score_cap is None else min(legacy_score_cap, 0.34)
        force_negative_label = True
        force_label = force_label or "Overrewarded Structure"
    elif moderate_market_structure_breach:
        activated.append("market_structure_floor_watchlist")
        quality_cap = 0.42 if quality_cap is None else min(quality_cap, 0.42)
        mispricing_cap = 0.34 if mispricing_cap is None else min(mispricing_cap, 0.34)
        confidence_cap = 0.55 if confidence_cap is None else min(confidence_cap, 0.55)
        fragility_floor = 0.70 if fragility_floor is None else max(fragility_floor, 0.70)
        legacy_score_cap = 0.42 if legacy_score_cap is None else min(legacy_score_cap, 0.42)

    if not snapshot.registration_allowed and snapshot.min_burn <= 0 and snapshot.max_burn <= 0 and snapshot.difficulty <= 0:
        activated.append("registration_closed_without_burn_or_pow_penalty")
        mispricing_cap = 0.18 if mispricing_cap is None else min(mispricing_cap, 0.18)
        confidence_cap = 0.50 if confidence_cap is None else min(confidence_cap, 0.50)
        fragility_floor = 0.75 if fragility_floor is None else max(fragility_floor, 0.75)
        legacy_score_cap = 0.32 if legacy_score_cap is None else min(legacy_score_cap, 0.32)
        force_negative_label = True
        force_label = "Dereg Candidate"

    liquid_flagship_concentration = (
        pool_depth >= 50_000
        and max_slippage <= 0.03
        and participation >= 0.45
        and (concentration_delta is None or concentration_delta <= 0.02)
    )
    market_relevant_concentration = (
        pool_depth >= 15_000
        and market_relevance >= 0.55
        and max_slippage <= 0.06
        and participation >= 0.30
        and (concentration_delta is None or concentration_delta <= 0.05)
    )

    if concentration > 0.60:
        activated.append("concentration_caps_fundamental_quality")
        if liquid_flagship_concentration:
            activated.append("liquid_flagship_concentration_watchlist")
            quality_cap = 0.52 if quality_cap is None else min(quality_cap, 0.52)
            fragility_floor = 0.58 if fragility_floor is None else max(fragility_floor, 0.58)
        elif market_relevant_concentration:
            activated.append("market_relevant_concentration_watchlist")
            quality_cap = 0.56 if quality_cap is None else min(quality_cap, 0.56)
            fragility_floor = 0.60 if fragility_floor is None else max(fragility_floor, 0.60)
        else:
            quality_cap = 0.42 if quality_cap is None else min(quality_cap, 0.42)
            fragility_floor = 0.65 if fragility_floor is None else max(fragility_floor, 0.65)

    if consensus_hollow:
        activated.append("uninformative_consensus_caps_confidence")
        quality_cap = 0.50 if quality_cap is None else min(quality_cap, 0.50)
        confidence_cap = 0.45 if confidence_cap is None else min(confidence_cap, 0.45)
        force_label = force_label or "Consensus Hollow"

    if snapshot.immunity_period <= 0 and (bundle.raw.get("dereg_risk_proxy") or 0.0) > 0.55:
        activated.append("post_immunity_high_dereg_risk_penalty")
        mispricing_cap = 0.15 if mispricing_cap is None else min(mispricing_cap, 0.15)
        fragility_floor = 0.80 if fragility_floor is None else max(fragility_floor, 0.80)
        legacy_score_cap = 0.24 if legacy_score_cap is None else min(legacy_score_cap, 0.24)
        force_negative_label = True
        force_label = force_label or "Dereg Candidate"

    if confidence_inputs < 0.30 and update_freshness < 0.30:
        activated.append("thin_evidence_caps_confidence")
        confidence_cap = 0.35 if confidence_cap is None else min(confidence_cap, 0.35)
        mispricing_cap = 0.20 if mispricing_cap is None else min(mispricing_cap, 0.20)

    if signal_fabrication_risk > 0.58:
        activated.append("signal_fabrication_risk_caps_mispricing")
        mispricing_cap = 0.36 if mispricing_cap is None else min(mispricing_cap, 0.36)
        confidence_cap = 0.46 if confidence_cap is None else min(confidence_cap, 0.46)
        fragility_floor = 0.68 if fragility_floor is None else max(fragility_floor, 0.68)

    if (
        low_evidence_high_conviction > 0.52
        or (
            underreaction_score > 0.62
            and confidence_inputs < 0.50
            and proxy_reliance > 0.52
            and thesis_coherence < 0.62
        )
    ):
        activated.append("low_evidence_high_conviction_caps_total")
        mispricing_cap = 0.32 if mispricing_cap is None else min(mispricing_cap, 0.32)
        confidence_cap = 0.44 if confidence_cap is None else min(confidence_cap, 0.44)
        legacy_score_cap = 0.40 if legacy_score_cap is None else min(legacy_score_cap, 0.40)

    if (
        crowding_proxy > 0.48
        and overreaction_score > 0.18
        and (
            concentration > 0.56
            or max_slippage > 0.035
            or staking_apy > 75
            or market_structure_floor < 0.68
        )
    ):
        activated.append("reflexive_market_structure_caps_confidence")
        confidence_cap = 0.44 if confidence_cap is None else min(confidence_cap, 0.44)
        mispricing_cap = 0.36 if mispricing_cap is None else min(mispricing_cap, 0.36)

    if (
        crowding_proxy > 0.55
        and (
            staking_apy > 85
            or market_structure_floor < 0.62
            or pool_depth < 25_000
        )
        and (
            concentration > 0.60
            or max_slippage > 0.04
            or signal_fabrication_risk > 0.42
        )
    ):
        activated.append("crowded_repricing_discount_caps_confidence")
        confidence_cap = 0.40 if confidence_cap is None else min(confidence_cap, 0.40)
        mispricing_cap = 0.34 if mispricing_cap is None else min(mispricing_cap, 0.34)
        fragility_floor = 0.68 if fragility_floor is None else max(fragility_floor, 0.68)

    return HardRuleResult(
        activated=activated,
        quality_cap=quality_cap,
        mispricing_cap=mispricing_cap,
        confidence_cap=confidence_cap,
        fragility_floor=fragility_floor,
        legacy_score_cap=legacy_score_cap,
        force_negative_label=force_negative_label,
        force_label=force_label,
    )


def apply_rule_caps(signals: PrimarySignals, rules: HardRuleResult) -> PrimarySignals:
    quality = min(signals.fundamental_quality, rules.quality_cap) if rules.quality_cap is not None else signals.fundamental_quality
    mispricing = min(signals.mispricing_signal, rules.mispricing_cap) if rules.mispricing_cap is not None else signals.mispricing_signal
    confidence = min(signals.signal_confidence, rules.confidence_cap) if rules.confidence_cap is not None else signals.signal_confidence
    fragility = max(signals.fragility_risk, rules.fragility_floor) if rules.fragility_floor is not None else signals.fragility_risk
    return PrimarySignals(
        fundamental_quality=quality,
        mispricing_signal=mispricing,
        fragility_risk=fragility,
        signal_confidence=confidence,
    )
