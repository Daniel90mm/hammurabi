"""Unit tests for the economy: flat income + skill-based build attempts."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agents import AgentPool, Role, State  # noqa: E402
from economy import (  # noqa: E402
    EconomyConfig,
    apply_capital_returns,
    attempt_builds,
    decay_houses,
    earn_income,
    update_price,
)

# Build success depends on skill; disable random failure for deterministic tests.
NEVER_FAIL = dict(base_fail_rate=0.0, max_fail_rate=0.0)
ALWAYS_FAIL = dict(base_fail_rate=1.0, max_fail_rate=0.0)


def _pool(roles, *, wealth=100.0, has_house=False, state=State.ACTIVE, skill=0.5):
    """Housing is universal, so builders are also occupant candidates. To keep
    the resident-focused tests deterministic, builders are pre-housed here (a
    working builder has a home) -- they act purely as suppliers."""
    roles_arr = np.array(roles, dtype=np.int8)
    n = len(roles)
    hh = np.full(n, has_house, dtype=bool)
    hh[roles_arr == Role.BUILDER] = True
    return AgentPool(
        role=roles_arr,
        state=np.full(n, state, dtype=np.int8),
        skill=np.full(n, float(skill), dtype=np.float64),
        wealth=np.full(n, float(wealth), dtype=np.float64),
        has_house=hh,
        prison_remaining=np.zeros(n, dtype=np.int32),
        house_quality=np.where(hh, 0.5, 0.0).astype(np.float64),
    )


def test_income_paid_to_active_only():
    pool = _pool([Role.BUILDER, Role.RESIDENT])  # skill 0.5 -> earns exactly base
    pool.state[1] = State.DEAD
    pool.wealth[:] = 0.0
    earn_income(pool, EconomyConfig(base_income=10.0))
    assert pool.wealth[0] == 10.0  # active builder paid (skill 0.5 -> base)
    assert pool.wealth[1] == 0.0  # dead resident not paid


def test_income_scales_with_skill():
    pool = _pool([Role.RESIDENT, Role.RESIDENT, Role.RESIDENT])
    pool.skill[:] = [0.0, 0.5, 1.0]
    pool.wealth[:] = 0.0
    cfg = EconomyConfig(base_income=10.0, income_skill_min=0.4)
    earn_income(pool, cfg)
    assert pool.wealth[0] == 4.0  # skill 0 -> 0.4 * base
    assert pool.wealth[1] == 10.0  # skill 0.5 -> base
    assert pool.wealth[2] == 16.0  # skill 1 -> 1.6 * base


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
    assert list(info["failed_occupants"]) == [1]


def test_skilled_builder_still_fails_at_the_floor():
    # Max skill removes the skill-dependent term, but the floor remains.
    pool = _pool([Role.BUILDER, Role.RESIDENT], wealth=200.0, skill=1.0)
    cfg = EconomyConfig(base_fail_rate=1.0, max_fail_rate=0.0)
    info = attempt_builds(pool, cfg, np.random.default_rng(0))
    assert info["houses_built"] == 0
    assert list(info["failed_builders"]) == [0]


def test_builders_are_also_housed_universal_housing():
    # 50 houseless builders -> they build each other's houses (not their own).
    n = 50
    pool = AgentPool(
        role=np.full(n, Role.BUILDER, np.int8),
        state=np.full(n, State.ACTIVE, np.int8),
        skill=np.full(n, 0.9),
        wealth=np.full(n, 500.0),
        has_house=np.zeros(n, bool),  # all houseless
        prison_remaining=np.zeros(n, np.int32),
        house_quality=np.zeros(n, np.float64),
    )
    info = attempt_builds(pool, EconomyConfig(**NEVER_FAIL), np.random.default_rng(0))
    assert info["houses_built"] > 0  # builders housing builders
    assert pool.has_house.sum() == info["houses_built"]
    assert pool.wealth.sum() == 50 * 500.0  # transfers conserve total wealth


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


def test_capital_returns_proportional_to_wealth_and_skip_inactive():
    pool = _pool([Role.RESIDENT, Role.RESIDENT], wealth=200.0)
    pool.wealth[:] = [100.0, 300.0]
    pool.state[1] = State.DEAD  # inactive earns no return
    cfg = EconomyConfig(wealth_return_rate=0.1)
    cap = apply_capital_returns(pool, cfg)
    assert cap[0] == 10.0  # 0.1 * 100
    assert cap[1] == 0.0  # dead -> no capital income
    assert pool.wealth[0] == 110.0  # return added to the stock
    assert pool.wealth[1] == 300.0


def test_price_rises_when_demand_exceeds_supply():
    cfg = EconomyConfig(price_adjust_speed=0.1)
    assert update_price(100.0, demand=90, supply=10, config=cfg) > 100.0


def test_price_falls_when_supply_exceeds_demand():
    cfg = EconomyConfig(price_adjust_speed=0.1)
    assert update_price(100.0, demand=10, supply=90, config=cfg) < 100.0


def test_price_is_clamped_to_bounds():
    cfg = EconomyConfig(price_adjust_speed=0.1, price_min=50.0, price_max=200.0)
    assert update_price(1.0, demand=0, supply=100, config=cfg) == 50.0  # floor
    assert update_price(1e9, demand=100, supply=0, config=cfg) == 200.0  # ceiling


def test_price_stable_when_balanced():
    cfg = EconomyConfig(price_adjust_speed=0.1)
    assert update_price(100.0, demand=50, supply=50, config=cfg) == 100.0


def test_decay_sends_housed_residents_back_to_market():
    pool = _pool([Role.RESIDENT, Role.RESIDENT], has_house=True)
    # rate 1.0 -> every house wears out this tick
    info = decay_houses(pool, EconomyConfig(house_decay_rate=1.0), np.random.default_rng(0))
    assert info["houses_decayed"] == 2
    assert not pool.has_house.any()


def test_shoddy_houses_decay_faster_than_well_built():
    # Two cohorts of 2000 housed agents: one shoddy (q=0.0), one expert (q=1.0).
    n = 4000
    pool = AgentPool(
        role=np.full(n, Role.RESIDENT, np.int8),
        state=np.full(n, State.ACTIVE, np.int8),
        skill=np.full(n, 0.5),
        wealth=np.full(n, 100.0),
        has_house=np.ones(n, bool),
        prison_remaining=np.zeros(n, np.int32),
        house_quality=np.concatenate([np.zeros(2000), np.ones(2000)]),
    )
    decay_houses(pool, EconomyConfig(house_decay_rate=0.2), np.random.default_rng(0))
    shoddy_gone = int((~pool.has_house[:2000]).sum())
    expert_gone = int((~pool.has_house[2000:]).sum())
    assert shoddy_gone > expert_gone  # shoddy houses wear out faster


def test_no_decay_when_rate_zero():
    pool = _pool([Role.RESIDENT], has_house=True)
    info = decay_houses(pool, EconomyConfig(house_decay_rate=0.0), np.random.default_rng(0))
    assert info["houses_decayed"] == 0
    assert pool.has_house.all()


def test_builds_capped_by_scarcer_side():
    # 1 builder, 3 needy residents -> at most 1 build this tick.
    pool = _pool(
        [Role.BUILDER, Role.RESIDENT, Role.RESIDENT, Role.RESIDENT], wealth=500.0
    )
    info = attempt_builds(pool, EconomyConfig(**NEVER_FAIL), np.random.default_rng(0))
    assert info["houses_built"] == 1
