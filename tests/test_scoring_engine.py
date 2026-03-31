from features.types import AxisScores
from regimes.hard_rules import HardRuleResult
from scoring.engine import _apply_total_cap


def test_apply_total_cap_keeps_plain_caps_for_non_negative_rules():
    axes = AxisScores(
        intrinsic_quality=0.9,
        economic_sustainability=0.9,
        reflexivity=0.2,
        stress_robustness=0.8,
        opportunity_gap=0.4,
    )
    rules = HardRuleResult(activated=[], total_cap=0.2, force_negative_label=False)
    assert _apply_total_cap(0.6, axes, rules) == 0.2


def test_apply_total_cap_preserves_ordering_for_negative_regimes():
    stronger_axes = AxisScores(
        intrinsic_quality=0.8,
        economic_sustainability=0.4,
        reflexivity=0.2,
        stress_robustness=0.7,
        opportunity_gap=-0.1,
    )
    weaker_axes = AxisScores(
        intrinsic_quality=0.3,
        economic_sustainability=0.2,
        reflexivity=0.8,
        stress_robustness=0.2,
        opportunity_gap=-0.4,
    )
    rules = HardRuleResult(activated=["inactive_subnet_blocks_positive_label"], total_cap=0.2, force_negative_label=True)

    stronger = _apply_total_cap(0.6, stronger_axes, rules)
    weaker = _apply_total_cap(0.6, weaker_axes, rules)

    assert stronger < 0.2
    assert weaker < stronger
