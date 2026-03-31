from features.types import AxisScores, FeatureBundle
from regimes.hard_rules import HardRuleResult
from stress.scenarios import StressTestResult


def assign_label(
    axes: AxisScores,
    bundle: FeatureBundle,
    stress: StressTestResult,
    rules: HardRuleResult,
) -> tuple[str, str]:
    intrinsic = axes.intrinsic_quality
    economic = axes.economic_sustainability
    reflexivity = axes.reflexivity
    opportunity = axes.opportunity_gap
    concentration = max(bundle.raw.get("validator_dominance") or 0.0, bundle.raw.get("incentive_concentration") or 0.0)
    informativeness = bundle.raw.get("meaningful_discrimination") or 0.0
    consensus_entropy = bundle.raw.get("validator_weight_entropy") or 0.0
    dereg_risk = bundle.raw.get("dereg_risk_proxy") or 0.0

    if rules.force_negative_label or (economic > 0.55 and reflexivity > 0.65 and stress.max_drawdown > 0.25):
        return "Fragile Yield Trap", "Yield optics dominate, but concentration and stress sensitivity make the structure brittle."
    if intrinsic > 0.70 and economic > 0.62 and reflexivity < 0.35 and stress.robustness > 0.65:
        return "Hidden Compounder", "Quality and sustainability are strong while reflexive distortion remains low."
    if intrinsic > 0.62 and opportunity > 0.22 and reflexivity < 0.45:
        return "Underappreciated Infrastructure", "Internal quality is ahead of visible market recognition."
    if intrinsic > 0.55 and economic < 0.45 and reflexivity < 0.45:
        return "Early Quality Build", "Quality signals are forming before liquidity and emissions fully validate the subnet."
    if consensus_entropy > 0.85 and informativeness < 0.15:
        return "Consensus Hollow", "Validators appear aligned, but the consensus is not meaningfully discriminating."
    if reflexivity > 0.68 and concentration > 0.55:
        return "Reflexive Crowded Trade", "Price and participation optics depend too heavily on flows and concentration."
    if concentration > 0.60 and stress.max_drawdown > 0.20:
        return "Overrewarded Structure", "The market is rewarding a structure that remains too concentrated and stress-sensitive."
    if dereg_risk > 0.55 or (stress.max_drawdown > 0.22 and opportunity < 0.0):
        return "Dereg Candidate", "Weak resilience and poor market-quality alignment suggest elevated downside and replacement risk."
    return "Under Review", "Signal mix is mixed; no single structural regime dominates yet."
