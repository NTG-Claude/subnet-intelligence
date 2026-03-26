"""
Unit-Tests für signals.py und normalizer.py
Fixtures: 10 realistische Dummy-Subnets
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
# 10-subnet dummy fixture
# ---------------------------------------------------------------------------

N = 10  # number of subnets


@pytest.fixture
def subnets():
    """10 synthetic subnets with realistic variation."""
    return [
        {
            "netuid": i,
            "market_cap_usd": (i + 1) * 500_000,
            "flow_30d": (i - 4) * 20_000,          # negative for low-index subnets
            "unique_stakers": 50 + i * 30,
            "liquidity_usd": (i + 1) * 80_000,
            "emission_percent": max(0.5, 3.0 - i * 0.2),
            "market_cap_percent": (i + 1) / 55,     # proportional, sums ~1
            "miner_count_now": 100 + i * 10,
            "miner_count_30d_ago": 90 + i * 8,
            "registrations_7d": i * 3,
            "weight_commits": 5 + i * 2,
            "incentive_scores": [0.1 * j / (i + 1) for j in range(1, 20)],
            "top3_stake_percent": max(0.05, 0.5 - i * 0.04),
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
        # [1, 2, 2, 3]: value=2 → rank should be 0.5
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
    def _cross(self, subnets):
        all_flow_ratios = [
            s["flow_30d"] / s["market_cap_usd"] if s["market_cap_usd"] else None
            for s in subnets
        ]
        return (
            all_flow_ratios,
            [s["unique_stakers"] for s in subnets],
            [s["liquidity_usd"] for s in subnets],
        )

    def test_output_in_range(self, subnets):
        all_fr, all_us, all_liq = self._cross(subnets)
        for s in subnets:
            score = capital_conviction_score(
                s["flow_30d"], s["market_cap_usd"], s["unique_stakers"], s["liquidity_usd"],
                all_fr, all_us, all_liq,
            )
            assert 0.0 <= score <= 1.0

    def test_higher_flow_scores_higher(self, subnets):
        all_fr, all_us, all_liq = self._cross(subnets)
        scores = [
            capital_conviction_score(
                s["flow_30d"], s["market_cap_usd"], s["unique_stakers"], s["liquidity_usd"],
                all_fr, all_us, all_liq,
            )
            for s in subnets
        ]
        # Last subnet has highest flow_30d and stakers → should score higher than first
        assert scores[-1] > scores[0]

    def test_none_flow_returns_low_score(self, subnets):
        all_fr, all_us, all_liq = self._cross(subnets)
        score = capital_conviction_score(
            None, None, None, None, all_fr, all_us, all_liq
        )
        assert score == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Signal 2: network_activity_score
# ---------------------------------------------------------------------------

class TestNetworkActivityScore:
    def _cross(self, subnets):
        growths = [
            (s["miner_count_now"] - s["miner_count_30d_ago"]) / s["miner_count_30d_ago"]
            for s in subnets
        ]
        return growths, [s["registrations_7d"] for s in subnets], [s["weight_commits"] for s in subnets]

    def test_output_in_range(self, subnets):
        all_g, all_r, all_w = self._cross(subnets)
        for s in subnets:
            score = network_activity_score(
                s["miner_count_now"], s["miner_count_30d_ago"],
                s["registrations_7d"], s["weight_commits"],
                all_g, all_r, all_w,
            )
            assert 0.0 <= score <= 1.0

    def test_higher_growth_scores_higher(self, subnets):
        all_g, all_r, all_w = self._cross(subnets)
        scores = [
            network_activity_score(
                s["miner_count_now"], s["miner_count_30d_ago"],
                s["registrations_7d"], s["weight_commits"],
                all_g, all_r, all_w,
            )
            for s in subnets
        ]
        assert scores[-1] > scores[0]

    def test_zero_miner_count_30d_ago(self, subnets):
        all_g, all_r, all_w = self._cross(subnets)
        score = network_activity_score(
            100, 0, 5, 10, all_g, all_r, all_w
        )
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# Signal 3: emission_efficiency_score
# ---------------------------------------------------------------------------

class TestEmissionEfficiencyScore:
    def _cross(self, subnets):
        return [
            s["market_cap_percent"] / s["emission_percent"] if s["emission_percent"] > 0 else None
            for s in subnets
        ]

    def test_output_in_range(self, subnets):
        all_r = self._cross(subnets)
        for s in subnets:
            score = emission_efficiency_score(
                s["emission_percent"], s["market_cap_percent"], all_r
            )
            assert 0.0 <= score <= 1.0

    def test_none_emission_returns_zero(self, subnets):
        all_r = self._cross(subnets)
        assert emission_efficiency_score(None, 0.1, all_r) == 0.0
        assert emission_efficiency_score(0.0, 0.1, all_r) == 0.0


# ---------------------------------------------------------------------------
# Signal 4: distribution_health_score
# ---------------------------------------------------------------------------

class TestDistributionHealthScore:
    def test_perfect_equality_max_score(self):
        equal_incentives = [1.0] * 20
        score = distribution_health_score(equal_incentives, top3_stake_percent=0.0)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_perfect_inequality_low_score(self):
        # One miner gets everything
        unequal = [0.0] * 19 + [1.0]
        score = distribution_health_score(unequal, top3_stake_percent=1.0)
        assert score < 0.2

    def test_output_in_range(self, subnets):
        for s in subnets:
            score = distribution_health_score(
                s["incentive_scores"], s["top3_stake_percent"]
            )
            assert 0.0 <= score <= 1.0

    def test_empty_incentives_pessimistic(self):
        score = distribution_health_score([], top3_stake_percent=0.5)
        assert score == pytest.approx(0.25, abs=0.01)  # 0.5*(1-1) + 0.5*(1-0.5)

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
