"""Emergent metrics computed from simulation state (pure functions).

These are the headline numbers the README measures and that the future country
comparator will score against real data. Kept as pure functions so they're
trivially testable and reusable by the stats panel, the charts, and validation.
"""

from __future__ import annotations

import numpy as np


def gini(values: np.ndarray) -> float:
    """Gini coefficient of a non-negative distribution, in [0, 1].

    0 = perfect equality, ->1 = one agent holds everything. Empty input or an
    all-zero distribution returns 0.0.
    """
    v = np.sort(np.asarray(values, dtype=np.float64))
    n = v.size
    if n == 0:
        return 0.0
    total = v.sum()
    if total <= 0:
        return 0.0
    # Relative mean-absolute-difference form: 2*Σ(i*v_i)/(n*Σv) - (n+1)/n
    index = np.arange(1, n + 1)
    return float((2.0 * np.sum(index * v)) / (n * total) - (n + 1) / n)
