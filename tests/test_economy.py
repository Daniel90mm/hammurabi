"""Unit tests for the economy: flat income + skill-based build attempts."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agents import AgentPool, Role, State  # noqa: E402
from economy import EconomyConfig, attempt_builds, earn_income  # noqa: E402

# Build success depends on skill; disable random failure for deterministic tests.
NEVER_FAIL = dict(max_fail_rate=0.0)
ALWAYS_FAIL = dict(max_fail_rate=1.0)


def _pool(roles, *, wealth=100.0, has_house=False, state=State.ACTIVE, skill=0.5):
    n = len(roles)
    return AgentPool(
        role=np.array(roles, dtype=np.int8),
        state=np.full(n, state, dtype=np.int8),
        skill=np.full(n, float(skill), dtype=np.float64),
        wealth=np.full(n, float(wealth), dtype=np.float64),
        has_house=np.full(n, has_house, dtype=bool),
        prison_remaining=np.zeros(n, dtype=np.int32),
    )


def test_income_paid_to_active_only():
    pool = _pool([Role.BUILDER, Role.RESIDENT])
    pool.state[1] = State.DEAD
    pool.wealth[:] = 0.0
    earn_income(pool, EconomyConfig(base_income=10.0))
    assert pool.wealth[0] == 10.0  # active builder paid
    assert pool.wealth[1] == 0.0  # dead resident not paid


def test_successful_build_transfers_and_conserves_wealth():
    pool = _pool([Role.BUILDER, Role.RESIDENT], wealth=200.0)
    cfg = EconomyConfig(house_price=100.0, **NEVER_FAIL)
    total_before = pool.wealth.sum()

    info = attempt_builds(pool, cfg, np.random.default_rng(0))

    assert info["houses_built"] == 1
    assert pool.has_house[1]  # resident now housed
    assert pool.wealth[1] == 100.0  # paid the price
    assert pool.wealth[0] == 300.0  # builder received it
    assert pool.wealth.sum() == total_before  # transfer is conserved


def test_failed_build_does_not_transact_and_reports_pair():
    # skill 0 + max_fail_rate 1.0 -> the build always fails.
    pool = _pool([Role.BUILDER, Role.RESIDENT], wealth=200.0, skill=0.0)
    info = attempt_builds(pool, EconomyConfig(**ALWAYS_FAIL), np.random.default_rng(0))

    assert info["houses_built"] == 0
    assert not pool.has_house[1]  # not housed
    assert pool.wealth[1] == 200.0  # no payment on failure
    assert list(info["failed_builders"]) == [0]
    assert list(info["failed_residents"]) == [1]


def test_resident_who_cannot_afford_is_skipped():
    pool = _pool([Role.BUILDER, Role.RESIDENT], wealth=50.0)
    info = attempt_builds(
        pool, EconomyConfig(house_price=100.0, **NEVER_FAIL), np.random.default_rng(0)
    )
    assert info["houses_built"] == 0
    assert not pool.has_house[1]


def test_already_housed_resident_not_rebuilt():
    pool = _pool([Role.BUILDER, Role.RESIDENT], wealth=500.0, has_house=True)
    info = attempt_builds(pool, EconomyConfig(**NEVER_FAIL), np.random.default_rng(0))
    assert info["houses_built"] == 0


def test_builds_capped_by_scarcer_side():
    # 1 builder, 3 needy residents -> at most 1 build this tick.
    pool = _pool(
        [Role.BUILDER, Role.RESIDENT, Role.RESIDENT, Role.RESIDENT], wealth=500.0
    )
    info = attempt_builds(pool, EconomyConfig(**NEVER_FAIL), np.random.default_rng(0))
    assert info["houses_built"] == 1
