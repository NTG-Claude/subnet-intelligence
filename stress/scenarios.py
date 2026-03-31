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


def _base_total(axes: AxisScores) -> float:
    return (
        0.34 * axes.intrinsic_quality
        + 0.28 * axes.economic_sustainability
        + 0.18 * (1.0 - axes.reflexivity)
        + 0.20 * axes.stress_robustness
    )


def run_stress_tests(snapshot: RawSubnetSnapshot, bundle: FeatureBundle, axes: AxisScores) -> StressTestResult:
    active_ratio = bundle.raw.get("active_ratio") or 0.0
    concentration = max(bundle.raw.get("validator_dominance") or 0.0, bundle.raw.get("incentive_concentration") or 0.0)
    liquidity = bundle.raw.get("liquidity_thinness") or 0.0
    informativeness = bundle.raw.get("meaningful_discrimination") or 0.0

    base = _base_total(axes)
    scenarios = [
        ("10% outflow shock", 0.10 * liquidity + 0.04 * concentration),
        ("20% outflow shock", 0.18 * liquidity + 0.08 * concentration),
        ("top validator removal", 0.10 + 0.20 * concentration),
        ("liquidity shock", 0.16 * max(liquidity, 0.15)),
        ("emission compression", 0.10 * max(0.0, 0.6 - active_ratio)),
        ("consensus perturbation", 0.14 * max(0.0, 0.5 - informativeness)),
        ("concentration shock", 0.18 * concentration),
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
