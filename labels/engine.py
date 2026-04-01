from features.types import AxisScores, FeatureBundle, PrimarySignals
from regimes.hard_rules import HardRuleResult
from stress.scenarios import StressTestResult


def _bundle_score(bundle: FeatureBundle, key: str, fallback: float = 0.0) -> float:
    if key in bundle.core_blocks:
        return bundle.core_blocks.get(key, fallback)
    if key in bundle.base_components:
        return bundle.base_components.get(key, fallback)
    return bundle.raw.get(key) or fallback


def assign_label(
    signals: PrimarySignals | AxisScores,
    bundle: FeatureBundle,
    stress: StressTestResult,
    rules: HardRuleResult,
) -> tuple[str, str]:
    if isinstance(signals, AxisScores):
        signals = PrimarySignals(
            fundamental_quality=max(
                0.0,
                min(
                    1.0,
                    0.55 * signals.intrinsic_quality
                    + 0.25 * signals.economic_sustainability
                    + 0.20 * max(0.0, 1.0 - signals.reflexivity),
                ),
            ),
            mispricing_signal=max(0.0, min(1.0, 0.5 + signals.opportunity_gap / 2.0)),
            fragility_risk=max(
                0.0,
                min(
                    1.0,
                    0.55 * max(0.0, 1.0 - signals.stress_robustness)
                    + 0.45 * signals.reflexivity,
                ),
            ),
            signal_confidence=max(0.0, min(1.0, 0.45 + 0.35 * signals.stress_robustness)),
        )

    fundamental = signals.fundamental_quality
    mispricing = signals.mispricing_signal
    fragility = signals.fragility_risk
    confidence = signals.signal_confidence
    fundamental_health = _bundle_score(bundle, "fundamental_health", fundamental)
    opportunity_underreaction = _bundle_score(bundle, "opportunity_underreaction", mispricing)
    market_legitimacy = _bundle_score(bundle, "market_legitimacy", bundle.raw.get("market_legitimacy") or bundle.raw.get("market_relevance_proxy") or 0.0)
    data_confidence = _bundle_score(bundle, "data_confidence", bundle.raw.get("data_confidence") or confidence)
    market_confidence = _bundle_score(bundle, "market_confidence", bundle.raw.get("market_confidence") or confidence)
    thesis_confidence = _bundle_score(bundle, "thesis_confidence", bundle.raw.get("thesis_confidence") or confidence)
    concentration = max(bundle.raw.get("validator_dominance") or 0.0, bundle.raw.get("incentive_concentration") or 0.0)
    price_lag = bundle.raw.get("price_response_lag_to_quality_shift") or 0.0
    sticky_usage = bundle.raw.get("emission_to_sticky_usage_conversion") or 0.0
    retention = bundle.raw.get("post_incentive_retention") or 0.0
    crowding = bundle.raw.get("crowding_proxy") or 0.0
    dereg_risk = bundle.raw.get("dereg_risk_proxy") or 0.0
    thin_liquidity = "thin_liquidity_caps_fragility" in rules.activated
    micro_pool = "micro_pool_apy_caps_total_score" in rules.activated
    inactive = "inactive_subnet_blocks_positive_label" in rules.activated
    confidence_capped = "thin_evidence_caps_confidence" in rules.activated

    if rules.force_label == "Consensus Hollow":
        return "Consensus Hollow", "Validator alignment exists, but the underlying signal is too uninformative to trust as investment evidence."
    if rules.force_label == "Dereg Candidate":
        return "Dereg Candidate", "Participation, liquidity, and survivability remain too weak, leaving elevated replacement risk for any investment thesis."
    if rules.force_label == "Overrewarded Structure":
        return "Overrewarded Structure", "Liquidity and ownership structure are too fragile for the current reward and pricing profile."

    if inactive or dereg_risk > 0.60:
        return "Dereg Candidate", "The structure is still too vulnerable to participation loss or replacement, leaving clear replacement risk in the thesis."
    if micro_pool or (thin_liquidity and crowding > 0.40):
        return "Overrewarded Structure", "Capital is paying for yield optics before the market structure is deep enough to support them."
    if fragility > 0.72 and concentration > 0.55:
        return "Fragile Yield Trap", "Economics may look attractive, but concentration, thin liquidity, and reversal risk make the setup brittle."
    if fundamental > 0.72 and fundamental_health > 0.70 and mispricing > 0.64 and fragility < 0.38 and confidence > 0.58 and market_confidence > 0.55:
        return "Hidden Compounder", "Quality is compounding faster than price, with enough durability and evidence quality to matter."
    if fundamental > 0.60 and opportunity_underreaction > 0.55 and mispricing > 0.58 and price_lag > 0.10 and confidence > 0.48 and market_legitimacy > 0.45:
        return "Underappreciated Infrastructure", "Structural improvement is visible in participation and liquidity, but market recognition is still lagging."
    if (
        fundamental > 0.62
        and fundamental_health > 0.58
        and fragility < 0.35
        and confidence > 0.45
        and thesis_confidence > 0.42
        and market_legitimacy > 0.40
        and concentration < 0.55
        and crowding < 0.35
    ):
        return "Early Quality Build", "Quality and resilience are already visible, even if the valuation gap is still modest and the thesis is early."
    if fundamental > 0.56 and fundamental_health > 0.50 and sticky_usage > 0.05 and retention > 0.05 and fragility < 0.55 and thesis_confidence > 0.45:
        return "Early Quality Build", "Usage and retention are improving in a way that looks earned rather than purely incentive-driven."
    if (
        (crowding > 0.55 and fragility > 0.50 and mispricing < 0.50)
        or (crowding > 0.50 and concentration > 0.58 and stress.max_drawdown > 0.20)
        or (concentration > 0.58 and fragility > 0.55 and mispricing < 0.50 and stress.max_drawdown > 0.20)
    ):
        return "Reflexive Crowded Trade", "The trade is increasingly crowded, reflexive, and vulnerable to reversals rather than driven by fresh underpricing."
    if confidence < 0.40 or data_confidence < 0.35 or thesis_confidence < 0.35 or confidence_capped:
        return "Under Review", "The signal is directionally interesting, but current evidence quality is too thin to treat it as investment-grade."
    return "Under Review", "Quality, valuation gap, fragility, and confidence are mixed, so the thesis remains provisional."
