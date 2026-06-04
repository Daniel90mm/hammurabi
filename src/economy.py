"""Simple economy: flat income and a fixed house price (build step 2).

This is the deliberately naive economy: everyone earns the same wage each tick,
and houses cost a fixed amount. There is no failure (step 3), no profession
switching (step 4), and no emergent pricing (step 5) yet -- only money moving.

Functions mutate the AgentPool arrays in place (structure-of-arrays) and return
a small dict of per-tick facts for logging/stats.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from agents import AgentPool, Role


@dataclass(frozen=True)
class EconomyConfig:
    """Tunable economic constants. These are *model knobs*, not founding
    parameters -- the four seeds live in FoundingParams."""

    base_income: float = 10.0  # flat wage paid to every active agent per tick
    house_price: float = 100.0  # fixed cost of one house (step 5 makes it emerge)


def earn_income(pool: AgentPool, config: EconomyConfig) -> dict[str, float]:
    """Pay the flat wage to every active agent.

    Income is created exogenously (an open economy / external wage), so total
    wealth grows -- this is not a conserved transfer.
    """
    active = pool.active_mask()
    pool.wealth[active] += config.base_income
    return {"wage_paid": config.base_income * int(np.count_nonzero(active))}


def build_houses(
    pool: AgentPool, config: EconomyConfig, rng: np.random.Generator
) -> dict[str, int]:
    """Match houseless active residents (who can afford it) with active builders.

    Step-2 matching is non-spatial and simple: each available builder builds at
    most one house this tick. We pair as many (builder, resident) as we can, the
    resident pays the fixed price to the builder, and the resident is housed.
    The price transfer is wealth-conserving.
    """
    active = pool.active_mask()

    builders = np.flatnonzero(active & (pool.role == Role.BUILDER))
    residents = np.flatnonzero(
        active
        & (pool.role == Role.RESIDENT)
        & ~pool.has_house
        & (pool.wealth >= config.house_price)
    )

    n_builds = int(min(builders.size, residents.size))
    if n_builds == 0:
        return {"houses_built": 0}

    # Random pairing -- shuffle both pools and zip the first n_builds of each.
    rng.shuffle(builders)
    rng.shuffle(residents)
    chosen_builders = builders[:n_builds]
    chosen_residents = residents[:n_builds]

    pool.wealth[chosen_residents] -= config.house_price
    pool.wealth[chosen_builders] += config.house_price
    pool.has_house[chosen_residents] = True

    return {"houses_built": n_builds}
