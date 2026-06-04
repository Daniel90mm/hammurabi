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
    base_fail_rate: float = 0.01  # irreducible failure floor: even a perfectly
    #                               skilled builder fails this often (bad luck)
    max_fail_rate: float = 0.10  # skill-dependent failure on top of the floor;
    #                              scales with (1 - skill)
    house_decay_rate: float = 0.02  # base per-tick chance a house wears out and
    #                                 the resident must rebuild (~1/rate ticks)
    decay_skill_factor: float = 1.0  # how strongly build quality moves the decay
    #   rate around the base: effective = base * (1 + factor*(0.5 - quality)).
    #   quality 0 (shoddy) decays faster; quality 1 (expert) decays slower.


def earn_income(pool: AgentPool, config: EconomyConfig) -> dict[str, float]:
    """Pay the flat wage to every active agent.

    Income is created exogenously (an open economy / external wage), so total
    wealth grows -- this is not a conserved transfer.
    """
    active = pool.active_mask()
    pool.wealth[active] += config.base_income
    return {"wage_paid": config.base_income * int(np.count_nonzero(active))}


def attempt_builds(
    pool: AgentPool, config: EconomyConfig, rng: np.random.Generator
) -> dict[str, object]:
    """Match builders to houseless residents and attempt each build.

    Step-2/3 matching is non-spatial and simple: each available builder builds at
    most one house this tick, paired randomly with a houseless, paying resident.

    Each pair then succeeds or fails based on the builder's skill
    (``fail_prob = base_fail_rate + (1 - skill) * max_fail_rate``, so even a
    perfectly skilled builder fails at the irreducible floor). On **success** the
    resident
    pays the fixed price to the builder (wealth-conserving) and is housed. On
    **failure** nothing is transacted -- the (builder, resident) pair is returned
    so the punishment layer can apply consequences; the resident stays houseless
    and may retry next tick.

    Returns
    -------
    {"houses_built": int,
     "failed_builders": np.ndarray[int],
     "failed_residents": np.ndarray[int]}
    """
    empty = np.empty(0, dtype=np.int64)
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
        return {"houses_built": 0, "failed_builders": empty, "failed_residents": empty}

    # Random pairing -- shuffle both pools and zip the first n_builds of each.
    rng.shuffle(builders)
    rng.shuffle(residents)
    pair_builders = builders[:n_builds]
    pair_residents = residents[:n_builds]

    fail_prob = np.clip(
        config.base_fail_rate
        + (1.0 - pool.skill[pair_builders]) * config.max_fail_rate,
        0.0,
        1.0,
    )
    failed = rng.random(n_builds) < fail_prob
    succeeded = ~failed

    ok_builders = pair_builders[succeeded]
    ok_residents = pair_residents[succeeded]
    pool.wealth[ok_residents] -= config.house_price
    pool.wealth[ok_builders] += config.house_price
    pool.has_house[ok_residents] = True
    # The house inherits the builder's skill as its build quality (drives decay).
    pool.house_quality[ok_residents] = pool.skill[ok_builders]

    return {
        "houses_built": int(succeeded.sum()),
        "failed_builders": pair_builders[failed],
        "failed_residents": pair_residents[failed],
    }


def decay_houses(
    pool: AgentPool, config: EconomyConfig, rng: np.random.Generator
) -> dict[str, int]:
    """Wear out houses: each housed agent's house decays with a constant hazard.

    A decayed house sends its owner back into the housing market (has_house ->
    False), renewing building demand so the economy does not freeze once
    everyone is initially housed.

    The hazard depends on build quality: a shoddy house (low-skill builder)
    decays faster, a well-built one (high-skill builder) slower --
    ``effective = base * (1 + factor*(0.5 - quality))`` clipped to [0, 1].
    """
    housed = np.flatnonzero(pool.has_house & pool.active_mask())
    if housed.size == 0:
        return {"houses_decayed": 0}
    eff_rate = np.clip(
        config.house_decay_rate
        * (1.0 + config.decay_skill_factor * (0.5 - pool.house_quality[housed])),
        0.0,
        1.0,
    )
    decayed = housed[rng.random(housed.size) < eff_rate]
    pool.has_house[decayed] = False
    pool.house_quality[decayed] = 0.0
    return {"houses_decayed": int(decayed.size)}
