"""Unit tests for emergent metrics."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from metrics import gini  # noqa: E402


def test_gini_of_perfect_equality_is_zero():
    assert gini(np.full(100, 50.0)) == 0.0


def test_gini_of_total_inequality_approaches_one():
    v = np.zeros(100)
    v[0] = 1000.0  # one agent holds everything
    assert gini(v) > 0.98  # -> (n-1)/n = 0.99


def test_gini_empty_and_allzero_are_zero():
    assert gini(np.array([])) == 0.0
    assert gini(np.zeros(10)) == 0.0


def test_gini_increases_with_spread():
    equalish = gini(np.array([40.0, 50.0, 60.0]))
    skewed = gini(np.array([1.0, 9.0, 140.0]))
    assert skewed > equalish
    assert 0.0 <= equalish <= 1.0 and 0.0 <= skewed <= 1.0
