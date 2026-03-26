"""
Score signals — 5 dimensions, each returns float in [0.0, 1.0].

All functions are pure: they take raw data + the full cross-subnet
dataset for normalisation and return a single float.
"""

from typing import Optional
import numpy as np

from scorer.normalizer import percentile_rank


# ---------------------------------------------------------------------------
# Signal 1 — Capital Conviction (weight 25)
# ---------------------------------------------------------------------------

def capital_conviction_score(
    net_flow_30d: Optional[float],
    market_cap_usd: Optional[float],
    unique_stakers: Optional[int],
    liquidity_usd: Optional[float],
    # Cross-subnet lists for percentile normalisation
    all_flow_ratios: list[Optional[float]],
    all_unique_stakers: list[Optional[int]],
    all_liquidity: list[Optional[float]],
) -> float:
    """
    Measures whether capital is actively moving INTO the subnet.

    flow_pct  = percentile_rank(net_flow_30d / market_cap)
    staker_pct = percentile_rank(unique_stakers)
    pool_pct   = percentile_rank(liquidity_usd)
    → 0.5 * flow_pct + 0.3 * staker_pct + 0.2 * pool_pct
    """
    if market_cap_usd and market_cap_usd > 0 and net_flow_30d is not None:
        flow_ratio: Optional[float] = net_flow_30d / market_cap_usd
    else:
        flow_ratio = None

    flow_pct = percentile_rank(flow_ratio, all_flow_ratios)
    staker_pct = percentile_rank(
        float(unique_stakers) if unique_stakers is not None else None,
        [float(x) if x is not None else None for x in all_unique_stakers],
    )
    pool_pct = percentile_rank(liquidity_usd, all_liquidity)

    return 0.5 * flow_pct + 0.3 * staker_pct + 0.2 * pool_pct


# ---------------------------------------------------------------------------
# Signal 2 — Network Activity (weight 25)
# ---------------------------------------------------------------------------

def network_activity_score(
    miner_count_now: Optional[int],
    miner_count_30d_ago: Optional[int],
    new_registrations_7d: Optional[int],
    weight_commits_per_epoch: Optional[int],
    # Cross-subnet lists
    all_miner_growths: list[Optional[float]],
    all_registrations: list[Optional[int]],
    all_weight_commits: list[Optional[int]],
) -> float:
    """
    Measures how actively miners and validators are participating.

    miner_growth = (now - 30d_ago) / 30d_ago
    growth_pct   = percentile_rank(miner_growth)
    reg_pct      = percentile_rank(new_registrations_7d)
    weights_pct  = percentile_rank(weight_commits_per_epoch)
    → 0.4 * growth_pct + 0.4 * reg_pct + 0.2 * weights_pct
    """
    if (
        miner_count_now is not None
        and miner_count_30d_ago is not None
        and miner_count_30d_ago > 0
    ):
        miner_growth: Optional[float] = (miner_count_now - miner_count_30d_ago) / miner_count_30d_ago
    else:
        miner_growth = None

    growth_pct = percentile_rank(miner_growth, all_miner_growths)
    reg_pct = percentile_rank(
        float(new_registrations_7d) if new_registrations_7d is not None else None,
        [float(x) if x is not None else None for x in all_registrations],
    )
    weights_pct = percentile_rank(
        float(weight_commits_per_epoch) if weight_commits_per_epoch is not None else None,
        [float(x) if x is not None else None for x in all_weight_commits],
    )

    return 0.4 * growth_pct + 0.4 * reg_pct + 0.2 * weights_pct


# ---------------------------------------------------------------------------
# Signal 3 — Emission Efficiency (weight 20)
# ---------------------------------------------------------------------------

def emission_efficiency_score(
    emission_percent: Optional[float],
    market_cap_percent: Optional[float],
    all_ratios: list[Optional[float]],
) -> float:
    """
    Measures how much market value the subnet generates per unit of emission.

    ratio = market_cap_percent / emission_percent  (>1.0 = efficient)
    → percentile_rank(ratio)
    """
    if (
        emission_percent is not None
        and emission_percent > 0
        and market_cap_percent is not None
    ):
        ratio: Optional[float] = market_cap_percent / emission_percent
    else:
        ratio = None

    return percentile_rank(ratio, all_ratios)


# ---------------------------------------------------------------------------
# Signal 4 — Distribution Health (weight 15)
# ---------------------------------------------------------------------------

def gini_coefficient(values: list[float]) -> float:
    """Compute Gini coefficient for a list of non-negative values."""
    arr = np.array([v for v in values if v >= 0], dtype=float)
    if len(arr) == 0 or arr.sum() == 0:
        return 0.0
    arr = np.sort(arr)
    n = len(arr)
    index = np.arange(1, n + 1)
    return float((2 * np.sum(index * arr) - (n + 1) * arr.sum()) / (n * arr.sum()))


def distribution_health_score(
    incentive_scores: list[float],
    top3_stake_percent: Optional[float],
) -> float:
    """
    Measures how evenly rewards and stake are distributed.

    gini = gini_coefficient(incentive_scores)
    → 0.5 * (1 - gini) + 0.5 * (1 - top3_stake_percent)

    Note: no cross-subnet percentile here — both inputs are already in [0, 1].
    """
    if incentive_scores:
        gini = gini_coefficient(incentive_scores)
    else:
        gini = 1.0  # worst case if no data

    stake_concentration = top3_stake_percent if top3_stake_percent is not None else 1.0

    return 0.5 * (1.0 - gini) + 0.5 * (1.0 - stake_concentration)


# ---------------------------------------------------------------------------
# Signal 5 — Development Activity (weight 15)
# ---------------------------------------------------------------------------

def development_activity_score(
    commits_30d: Optional[int],
    unique_contributors_30d: Optional[int],
    all_commits: list[Optional[int]],
    all_contributors: list[Optional[int]],
) -> float:
    """
    Measures open-source development velocity.

    commit_pct  = percentile_rank(commits_30d)
    contrib_pct = percentile_rank(unique_contributors_30d)
    → 0.6 * commit_pct + 0.4 * contrib_pct
    """
    commit_pct = percentile_rank(
        float(commits_30d) if commits_30d is not None else None,
        [float(x) if x is not None else None for x in all_commits],
    )
    contrib_pct = percentile_rank(
        float(unique_contributors_30d) if unique_contributors_30d is not None else None,
        [float(x) if x is not None else None for x in all_contributors],
    )

    return 0.6 * commit_pct + 0.4 * contrib_pct
