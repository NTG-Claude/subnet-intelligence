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
    stake_usd: Optional[float],
    unique_coldkeys: Optional[int],
    # Cross-subnet lists for percentile normalisation
    all_stakes_usd: list[Optional[float]],
    all_unique_coldkeys: list[Optional[int]],
) -> float:
    """
    Measures staked capital conviction for the subnet (on-chain, v2).

    stake_pct    = percentile_rank(total_stake * tao_price)
    coldkey_pct  = percentile_rank(unique_coldkeys)
    → 0.6 * stake_pct + 0.4 * coldkey_pct
    """
    stake_pct = percentile_rank(stake_usd, all_stakes_usd)
    coldkey_pct = percentile_rank(
        float(unique_coldkeys) if unique_coldkeys is not None else None,
        [float(x) if x is not None else None for x in all_unique_coldkeys],
    )

    return 0.6 * stake_pct + 0.4 * coldkey_pct


# ---------------------------------------------------------------------------
# Signal 2 — Network Activity (weight 25)
# ---------------------------------------------------------------------------

def network_activity_score(
    active_ratio: Optional[float],
    n_validators: Optional[int],
    # Cross-subnet lists
    all_active_ratios: list[Optional[float]],
    all_n_validators: list[Optional[int]],
) -> float:
    """
    Measures on-chain participation activity (v2).

    active_ratio = n_active_7d / n_total  (neurons that set weights in last 7 days)
    active_pct   = percentile_rank(active_ratio)
    val_pct      = percentile_rank(n_validators)
    → 0.6 * active_pct + 0.4 * val_pct
    """
    active_pct = percentile_rank(active_ratio, all_active_ratios)
    val_pct = percentile_rank(
        float(n_validators) if n_validators is not None else None,
        [float(x) if x is not None else None for x in all_n_validators],
    )

    return 0.6 * active_pct + 0.4 * val_pct


# ---------------------------------------------------------------------------
# Signal 3 — Emission Efficiency (weight 20)
# ---------------------------------------------------------------------------

def emission_efficiency_score(
    stake_per_emission: Optional[float],
    all_stake_per_emission: list[Optional[float]],
) -> float:
    """
    Measures how much stake the subnet attracted per unit of daily emission (v2).

    stake_per_emission = total_stake_tao / emission_per_block_tao
    Higher → subnet captures more stake per unit of inflation = more efficient.
    → percentile_rank(stake_per_emission)
    """
    return percentile_rank(stake_per_emission, all_stake_per_emission)


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
