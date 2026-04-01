from dataclasses import dataclass

from collectors.models import RawSubnetSnapshot
from features.types import AxisScores, FeatureBundle


@dataclass
class StressScenarioResult:
    name: str
    score_after: float
    drawdown: float


@dataclass
class StressTestResult:
    scenarios: list[StressScenarioResult]
    robustness: float
    fragility_class: str
    max_drawdown: float


def _bundle_score(bundle: FeatureBundle, key: str, fallback: float = 0.0) -> float:
    if key in bundle.core_blocks:
        return bundle.core_blocks.get(key, fallback)
    if key in bundle.base_components:
        return bundle.base_components.get(key, fallback)
    return bundle.raw.get(key) or fallback


def _base_total(axes: AxisScores) -> float:
    return (
        0.34 * axes.intrinsic_quality
        + 0.28 * axes.economic_sustainability
        + 0.18 * (1.0 - axes.reflexivity)
        + 0.20 * axes.stress_robustness
    )


def run_stress_tests(snapshot: RawSubnetSnapshot, bundle: FeatureBundle, axes: AxisScores) -> StressTestResult:
    participation_health = _bundle_score(
        bundle,
        "participation_health",
        bundle.raw.get("active_ratio") or 0.0,
    )
    validator_health = _bundle_score(
        bundle,
        "validator_health",
        bundle.raw.get("meaningful_discrimination") or 0.0,
    )
    liquidity_health = _bundle_score(
        bundle,
        "liquidity_health",
        1.0 - (bundle.raw.get("liquidity_thinness") or 0.0),
    )
    market_confidence = _bundle_score(
        bundle,
        "market_confidence",
        bundle.raw.get("market_confidence") or 0.0,
    )
    fundamental_health = _bundle_score(
        bundle,
        "fundamental_health",
        axes.intrinsic_quality,
    )
    market_legitimacy = _bundle_score(
        bundle,
        "market_legitimacy",
        bundle.raw.get("market_legitimacy") or bundle.raw.get("market_relevance_proxy") or 0.0,
    )
    crowding_level = _bundle_score(
        bundle,
        "crowding_level",
        bundle.raw.get("crowding_proxy") or 0.0,
    )
    concentration = _bundle_score(
        bundle,
        "concentration_risk",
        max(bundle.raw.get("validator_dominance") or 0.0, bundle.raw.get("incentive_concentration") or 0.0),
    )
    thin_liquidity_risk = _bundle_score(
        bundle,
        "thin_liquidity_risk",
        max(0.0, 1.0 - liquidity_health),
    )
    weak_market_structure = _bundle_score(
        bundle,
        "weak_market_structure",
        max(0.0, 1.0 - market_legitimacy),
    )

    base = _base_total(axes)
    scenarios = [
        ("10% outflow shock", 0.09 * thin_liquidity_risk + 0.05 * concentration + 0.03 * weak_market_structure),
        ("20% outflow shock", 0.17 * thin_liquidity_risk + 0.09 * concentration + 0.05 * weak_market_structure),
        ("top validator removal", 0.08 + 0.20 * concentration + 0.06 * max(0.0, 0.55 - validator_health)),
        ("liquidity shock", 0.18 * max(thin_liquidity_risk, 0.15) + 0.04 * weak_market_structure),
        ("emission compression", 0.08 * max(0.0, 0.55 - participation_health) + 0.06 * max(0.0, 0.55 - fundamental_health)),
        ("consensus perturbation", 0.10 * max(0.0, 0.55 - validator_health) + 0.08 * max(0.0, 0.55 - market_confidence)),
        ("concentration shock", 0.16 * concentration + 0.06 * crowding_level),
    ]

    results: list[StressScenarioResult] = []
    for name, penalty in scenarios:
        score_after = max(0.0, base - penalty)
        results.append(StressScenarioResult(name=name, score_after=score_after, drawdown=max(0.0, base - score_after)))

    max_drawdown = max((result.drawdown for result in results), default=0.0)
    robustness = max(0.0, 1.0 - max_drawdown / max(base, 0.20))
    if max_drawdown >= 0.35:
        fragility = "fragile"
    elif max_drawdown >= 0.18:
        fragility = "watchlist"
    else:
        fragility = "robust"

    return StressTestResult(
        scenarios=results,
        robustness=robustness,
        fragility_class=fragility,
        max_drawdown=max_drawdown,
    )
