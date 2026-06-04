"""Unit tests for profession switching (the ρ seed)."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agents import AgentPool, Role, State  # noqa: E402
from profession import ProfessionConfig, switch_professions  # noqa: E402


def _pool(roles, wealth):
    n = len(roles)
    return AgentPool(
        role=np.array(roles, dtype=np.int8),
        state=np.full(n, State.ACTIVE, dtype=np.int8),
        skill=np.full(n, 0.5, dtype=np.float64),
        wealth=np.array(wealth, dtype=np.float64),
        has_house=np.ones(n, dtype=bool),
        prison_remaining=np.zeros(n, dtype=np.int32),
        house_quality=np.full(n, 0.5, dtype=np.float64),
    )


# Half builders, half residents; builders much richer in most tests.
def _split(n_each, b_wealth, r_wealth):
    roles = [Role.BUILDER] * n_each + [Role.RESIDENT] * n_each
    wealth = [b_wealth] * n_each + [r_wealth] * n_each
    return _pool(roles, wealth)


def test_residents_join_building_when_builders_richer():
    pool = _split(50, b_wealth=500.0, r_wealth=100.0)
    cfg = ProfessionConfig(base_switch_rate=1.0)  # everyone eligible switches
    stats = switch_professions(
        pool, cfg, 1.0, builder_income=500.0, resident_income=100.0,
        rng=np.random.default_rng(0),
    )
    assert stats["to_builder"] == 50  # all residents switched
    assert stats["to_resident"] == 0


def test_risk_tolerance_zero_blocks_entry_to_building():
    pool = _split(50, b_wealth=500.0, r_wealth=100.0)
    cfg = ProfessionConfig(base_switch_rate=1.0)
    stats = switch_professions(
        pool, cfg, 0.0, builder_income=500.0, resident_income=100.0,
        rng=np.random.default_rng(0),
    )
    assert stats["to_builder"] == 0  # nobody dares enter the dangerous trade


def test_builders_flee_when_residents_richer_and_lose_house():
    pool = _split(50, b_wealth=100.0, r_wealth=500.0)
    cfg = ProfessionConfig(base_switch_rate=1.0)
    stats = switch_professions(
        pool, cfg, 0.0, builder_income=100.0, resident_income=500.0,
        rng=np.random.default_rng(0),
    )
    # risk aversion (1 - rho) = 1.0 -> all builders flee
    assert stats["to_resident"] == 50
    # the fled builders (indices 0..49) are now residents and lost their houses,
    # while the original residents (50..99) keep theirs.
    assert (pool.role[:50] == Role.RESIDENT).all()
    assert not pool.has_house[:50].any()
    assert pool.has_house[50:].all()


def test_no_switch_within_threshold():
    pool = _split(50, b_wealth=101.0, r_wealth=100.0)
    cfg = ProfessionConfig(base_switch_rate=1.0, gap_threshold=0.05)
    stats = switch_professions(
        pool, cfg, 1.0, builder_income=101.0, resident_income=100.0,  # ~1% < 5%
        rng=np.random.default_rng(0),
    )
    assert stats == {"to_builder": 0, "to_resident": 0}


def test_no_switch_when_a_role_is_empty():
    pool = _pool([Role.BUILDER, Role.BUILDER], [500.0, 500.0])
    cfg = ProfessionConfig(base_switch_rate=1.0)
    stats = switch_professions(
        pool, cfg, 1.0, builder_income=500.0, resident_income=100.0,
        rng=np.random.default_rng(0),
    )
    assert stats == {"to_builder": 0, "to_resident": 0}
