"""
Unit-Tests für signals.py und normalizer.py
Fixtures: 10 realistische Dummy-Subnets (v2 on-chain signals)
"""

import pytest
from scorer.normalizer import percentile_rank
from scorer.signals import (
    capital_conviction_score,
    development_activity_score,
    distribution_health_score,
    emission_efficiency_score,
    gini_coefficient,
    network_activity_score,
)

# ---------------------------------------------------------------------------
# 10-subnet dummy fixture (v2 on-chain fields)
# ---------------------------------------------------------------------------

N = 10


@pytest.fixture
def subnets():
    """10 synthetic subnets with realistic on-chain variation."""
    return [
        {
            "netuid": i,
            "stake_usd": (i + 1) * 200_000.0,
            "unique_coldkeys": 50 + i * 30,
            "active_ratio": 0.3 + i * 0.06,
            "n_validators": 5 + i * 2,
            "stake_per_emission": (i + 1) * 500.0,
            "incentive_scores": [0.1 * j / (i + 1) for j in range(1, 20)],
            "top3_stake_fraction": max(0.05, 0.5 - i * 0.04),
            "commits_30d": i * 15,
            "contributors_30d": max(1, i * 2),
        }
        for i in range(N)
    ]


# ---------------------------------------------------------------------------
# normalizer
# ---------------------------------------------------------------------------

class TestPercentileRank:
    def test_middle_value(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert percentile_rank(3.0, values) == pytest.approx(0.5, abs=0.01)

    def test_minimum_value(self):
        values = [1.0, 2.0, 3.0]
        assert percentile_rank(1.0, values) == pytest.approx(0.0, abs=0.01)

    def test_maximum_value(self):
        values = [1.0, 2.0, 3.0]
        assert percentile_rank(3.0, values) == pytest.approx(1.0, abs=0.01)

    def test_none_input_returns_zero(self):
        assert percentile_rank(None, [1.0, 2.0, 3.0]) == 0.0

    def test_nan_input_returns_zero(self):
        assert percentile_rank(float("nan"), [1.0, 2.0]) == 0.0

    def test_all_none_list_returns_zero(self):
        assert percentile_rank(1.0, [None, None]) == 0.0

    def test_ties_average_method(self):
        result = percentile_rank(2.0, [1.0, 2.0, 2.0, 3.0])
        assert result == pytest.approx(0.5, abs=0.01)

    def test_single_element_list(self):
        assert percentile_rank(5.0, [5.0]) == pytest.approx(0.0, abs=0.01)

    def test_output_bounded(self):
        values = [float(i) for i in range(100)]
        for v in values:
            r = percentile_rank(v, values)
            assert 0.0 <= r <= 1.0


# ---------------------------------------------------------------------------
# Signal 1: capital_conviction_score
# ---------------------------------------------------------------------------

class TestCapitalConvictionScore:
    def test_output_in_range(self, subnets):
        all_stakes = [s["stake_usd"] for s in subnets]
        all_ck = [s["unique_coldkeys"] for s in subnets]
        for s in subnets:
            score = capital_conviction_score(
                s["stake_usd"], s["unique_coldkeys"], all_stakes, all_ck
            )
            assert 0.0 <= score <= 1.0

    def test_higher_stake_scores_higher(self, subnets):
        all_stakes = [s["stake_usd"] for s in subnets]
        all_ck = [s["unique_coldkeys"] for s in subnets]
        scores = [
            capital_conviction_score(s["stake_usd"], s["unique_coldkeys"], all_stakes, all_ck)
            for s in subnets
        ]
        assert scores[-1] > scores[0]

    def test_none_inputs_return_zero(self, subnets):
        all_stakes = [s["stake_usd"] for s in subnets]
        all_ck = [s["unique_coldkeys"] for s in subnets]
        score = capital_conviction_score(None, None, all_stakes, all_ck)
        assert score == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Signal 2: network_activity_score
# ---------------------------------------------------------------------------

class TestNetworkActivityScore:
    def test_output_in_range(self, subnets):
        all_ar = [s["active_ratio"] for s in subnets]
        all_val = [s["n_validators"] for s in subnets]
        for s in subnets:
            score = network_activity_score(s["active_ratio"], s["n_validators"], all_ar, all_val)
            assert 0.0 <= score <= 1.0

    def test_higher_activity_scores_higher(self, subnets):
        all_ar = [s["active_ratio"] for s in subnets]
        all_val = [s["n_validators"] for s in subnets]
        scores = [
            network_activity_score(s["active_ratio"], s["n_validators"], all_ar, all_val)
            for s in subnets
        ]
        assert scores[-1] > scores[0]

    def test_none_inputs_return_zero(self, subnets):
        all_ar = [s["active_ratio"] for s in subnets]
        all_val = [s["n_validators"] for s in subnets]
        score = network_activity_score(None, None, all_ar, all_val)
        assert score == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Signal 3: emission_efficiency_score
# ---------------------------------------------------------------------------

class TestEmissionEfficiencyScore:
    def test_output_in_range(self, subnets):
        all_spe = [s["stake_per_emission"] for s in subnets]
        for s in subnets:
            score = emission_efficiency_score(s["stake_per_emission"], all_spe)
            assert 0.0 <= score <= 1.0

    def test_none_returns_zero(self, subnets):
        all_spe = [s["stake_per_emission"] for s in subnets]
        assert emission_efficiency_score(None, all_spe) == 0.0

    def test_higher_stake_per_emission_scores_higher(self, subnets):
        all_spe = [s["stake_per_emission"] for s in subnets]
        scores = [emission_efficiency_score(s["stake_per_emission"], all_spe) for s in subnets]
        assert scores[-1] > scores[0]


# ---------------------------------------------------------------------------
# Signal 4: distribution_health_score
# ---------------------------------------------------------------------------

class TestDistributionHealthScore:
    def test_perfect_equality_max_score(self):
        equal_incentives = [1.0] * 20
        score = distribution_health_score(equal_incentives, top3_stake_percent=0.0)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_perfect_inequality_low_score(self):
        unequal = [0.0] * 19 + [1.0]
        score = distribution_health_score(unequal, top3_stake_percent=1.0)
        assert score < 0.2

    def test_output_in_range(self, subnets):
        for s in subnets:
            score = distribution_health_score(s["incentive_scores"], s["top3_stake_fraction"])
            assert 0.0 <= score <= 1.0

    def test_empty_incentives_pessimistic(self):
        score = distribution_health_score([], top3_stake_percent=0.5)
        assert score == pytest.approx(0.25, abs=0.01)

    def test_none_top3_pessimistic(self):
        score = distribution_health_score([0.5, 0.5], top3_stake_percent=None)
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# Signal 5: development_activity_score
# ---------------------------------------------------------------------------

class TestDevelopmentActivityScore:
    def _cross(self, subnets):
        return [s["commits_30d"] for s in subnets], [s["contributors_30d"] for s in subnets]

    def test_output_in_range(self, subnets):
        all_c, all_contrib = self._cross(subnets)
        for s in subnets:
            score = development_activity_score(
                s["commits_30d"], s["contributors_30d"], all_c, all_contrib
            )
            assert 0.0 <= score <= 1.0

    def test_none_commits_returns_zero(self, subnets):
        all_c, all_contrib = self._cross(subnets)
        score = development_activity_score(None, None, all_c, all_contrib)
        assert score == pytest.approx(0.0)

    def test_most_active_scores_highest(self, subnets):
        all_c, all_contrib = self._cross(subnets)
        scores = [
            development_activity_score(
                s["commits_30d"], s["contributors_30d"], all_c, all_contrib
            )
            for s in subnets
        ]
        assert scores[-1] > scores[0]


# ---------------------------------------------------------------------------
# gini_coefficient
# ---------------------------------------------------------------------------

class TestGiniCoefficient:
    def test_perfect_equality(self):
        assert gini_coefficient([1.0, 1.0, 1.0, 1.0]) == pytest.approx(0.0, abs=0.001)

    def test_perfect_inequality(self):
        values = [0.0, 0.0, 0.0, 1.0]
        g = gini_coefficient(values)
        assert g > 0.6

    def test_empty_list(self):
        assert gini_coefficient([]) == 0.0

    def test_all_zeros(self):
        assert gini_coefficient([0.0, 0.0, 0.0]) == 0.0

    def test_output_bounded(self, subnets):
        for s in subnets:
            g = gini_coefficient(s["incentive_scores"])
            assert 0.0 <= g <= 1.0
