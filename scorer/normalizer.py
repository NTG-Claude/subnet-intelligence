"""
Normalizer — percentile rank utility
"""

from typing import Optional
import numpy as np


def percentile_rank(value: Optional[float], all_values: list[Optional[float]]) -> float:
    """
    Return the percentile rank of `value` within `all_values` as a float in [0.0, 1.0].

    - None / NaN inputs → 0.0 (pessimistic)
    - Ties → average method (matches scipy.stats.percentileofscore default)
    - If all values are None/NaN → 0.0
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return 0.0

    clean: list[float] = [
        v for v in all_values if v is not None and not (isinstance(v, float) and np.isnan(v))
    ]
    if not clean:
        return 0.0

    arr = np.array(clean, dtype=float)
    n = len(arr)
    if n == 1:
        return 0.0

    below = int(np.sum(arr < value))
    equal = int(np.sum(arr == value))
    # Maps min → 0.0, max → 1.0, middle → 0.5, ties → average
    rank = (2 * below + equal - 1) / (2 * (n - 1))
    return float(np.clip(rank, 0.0, 1.0))
