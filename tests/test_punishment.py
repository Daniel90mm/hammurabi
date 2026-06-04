"""Unit tests for the punishment spectrum (the P seed)."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agents import AgentPool, Role, State  # noqa: E402
from punishment import (  # noqa: E402
    PunishmentConfig,
    apply_failures,
    punishment_probs,
    tick_prisons,
)


def _pool(roles, *, wealth=500.0):
    n = len(roles)
    return AgentPool(
        role=np.array(roles, dtype=np.int8),
        state=np.full(n, State.ACTIVE, dtype=np.int8),
        skill=np.full(n, 0.5, dtype=np.float64),
        wealth=np.full(n, float(wealth), dtype=np.float64),
        has_house=np.zeros(n, dtype=bool),
        prison_remaining=np.zeros(n, dtype=np.int32),
        house_quality=np.zeros(n, dtype=np.float64),
    )


# --- the continuous P -> (death, prison, fine) blend ---


@pytest.mark.parametrize(
    "p, expected",
    [
        (0.0, (1.0, 0.0, 0.0)),  # Hammurabi: always death
        (0.5, (0.0, 1.0, 0.0)),  # imprisonment
        (1.0, (0.0, 0.0, 1.0)),  # compensatory: always fine
        (0.25, (0.5, 0.5, 0.0)),  # halfway death<->prison
        (0.75, (0.0, 0.5, 0.5)),  # halfway prison<->fine
    ],
)
def test_punishment_probs_anchors_and_interpolation(p, expected):
    assert punishment_probs(p) == pytest.approx(expected)


def test_probs_always_sum_to_one():
    for p in np.linspace(0, 1, 21):
        assert sum(punishment_probs(float(p))) == pytest.approx(1.0)


# --- applying consequences at the regime anchors ---


def _failure(pool):
    """One failed build: builder 0 built the failed house for resident 1."""
    return np.array([0]), np.array([1])


def test_hammurabi_kills_the_builder():
    pool = _pool([Role.BUILDER, Role.RESIDENT])
    fb, fr = _failure(pool)
    # resident_death_prob 0 isolates the builder outcome.
    cfg = PunishmentConfig(resident_death_prob=0.0)
    stats = apply_failures(pool, cfg, 0.0, np.random.default_rng(0), fb, fr)
    assert pool.state[0] == State.DEAD
    assert stats["builder_deaths"] == 1


def test_midpoint_imprisons_the_builder():
    pool = _pool([Role.BUILDER, Role.RESIDENT])
    fb, fr = _failure(pool)
    cfg = PunishmentConfig(resident_death_prob=0.0, prison_ticks=10)
    stats = apply_failures(pool, cfg, 0.5, np.random.default_rng(0), fb, fr)
    assert pool.state[0] == State.IMPRISONED
    assert pool.prison_remaining[0] == 10
    assert stats["imprisonments"] == 1


def test_compensatory_fines_the_builder():
    pool = _pool([Role.BUILDER, Role.RESIDENT], wealth=500.0)
    fb, fr = _failure(pool)
    cfg = PunishmentConfig(resident_death_prob=0.0, fine_amount=150.0)
    stats = apply_failures(pool, cfg, 1.0, np.random.default_rng(0), fb, fr)
    assert pool.state[0] == State.ACTIVE  # stays active
    assert pool.wealth[0] == 350.0  # paid the fine
    assert stats["fines"] == 1


def test_fine_capped_at_builder_wealth():
    pool = _pool([Role.BUILDER, Role.RESIDENT], wealth=50.0)
    fb, fr = _failure(pool)
    cfg = PunishmentConfig(resident_death_prob=0.0, fine_amount=150.0)
    apply_failures(pool, cfg, 1.0, np.random.default_rng(0), fb, fr)
    assert pool.wealth[0] == 0.0  # cannot go into debt


def test_occupant_can_die_in_collapse():
    pool = _pool([Role.BUILDER, Role.RESIDENT])
    fb, fr = _failure(pool)
    cfg = PunishmentConfig(resident_death_prob=1.0)  # always kills
    stats = apply_failures(pool, cfg, 1.0, np.random.default_rng(0), fb, fr)
    assert pool.state[1] == State.DEAD
    assert stats["resident_deaths"] == 1


def test_tick_prisons_releases_when_sentence_ends():
    pool = _pool([Role.BUILDER])
    pool.state[0] = State.IMPRISONED
    pool.prison_remaining[0] = 2
    assert tick_prisons(pool) == 0
    assert pool.state[0] == State.IMPRISONED
    assert tick_prisons(pool) == 1  # released on the second tick
    assert pool.state[0] == State.ACTIVE
    assert pool.prison_remaining[0] == 0
