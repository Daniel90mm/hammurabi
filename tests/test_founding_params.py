"""Unit tests for FoundingParams range validation (a pure function)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from simulation import FoundingParams  # noqa: E402


def _valid() -> dict:
    return dict(
        population=1_000,
        skill_variance=0.15,
        risk_tolerance=0.5,
        punishment=0.5,
    )


def test_valid_params_construct():
    p = FoundingParams(**_valid())
    assert p.population == 1_000


@pytest.mark.parametrize(
    "field, bad_value",
    [
        ("population", 99),
        ("population", 100_001),
        ("skill_variance", 0.0),
        ("skill_variance", 0.51),
        ("risk_tolerance", 0.09),
        ("risk_tolerance", 0.91),
        ("punishment", -0.01),
        ("punishment", 1.01),
    ],
)
def test_out_of_range_rejected(field, bad_value):
    args = _valid()
    args[field] = bad_value
    with pytest.raises(ValueError):
        FoundingParams(**args)


@pytest.mark.parametrize(
    "field, edge",
    [
        ("population", 100),
        ("population", 100_000),
        ("skill_variance", 0.01),
        ("skill_variance", 0.5),
        ("punishment", 0.0),
        ("punishment", 1.0),
    ],
)
def test_boundaries_accepted(field, edge):
    args = _valid()
    args[field] = edge
    FoundingParams(**args)  # must not raise
