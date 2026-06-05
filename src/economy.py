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
    house_price: float = 100.0  # *starting* price; it now emerges (see update_price)
    price_adjust_speed: float = 0.10  # max fractional price move per tick (at the
    #                                   extremes of demand/supply imbalance)
    price_min: float = 10.0  # price floor
    price_max: float = 10_000.0  # price ceiling (prevents runaway)
    base_fail_rate: float = 0.01  # irreducible failure floor: even a perfectly
    #                               skilled builder fails this often (bad luck)
    max_fail_rate: float = 0.10  # skill-dependent failure on top of the floor;
    #                              scales with (1 - skill)
    house_decay_rate: float = 0.02  # base per-tick chance a house wears out and
    #                                 the resident must rebuild (~1/rate ticks)
    decay_skill_factor: float = 1.0  # how strongly build quality moves the decay
    #   rate around the base: effective = base * (1 + factor*(0.5 - quality)).
    #   quality 0 (shoddy) decays faster; quality 1 (expert) decays slower.
    income_skill_min: float = 0.4  # wage scales with skill, not flat: a skill-0
    #   agent earns this fraction of base, skill-1 earns (2 - this); skill 0.5
    #   earns exactly base. Sustains wealth dispersion so σ drives inequality.


def earn_income(pool: AgentPool, config: EconomyConfig) -> dict[str, float]:
    """Pay a skill-scaled wage to every active agent.

    Wage = base * (income_skill_min + (1 - income_skill_min) * 2 * skill), so a
    skill-0 agent earns ``income_skill_min`` of base, skill-1 earns ``2 -
    income_skill_min``, and skill-0.5 earns exactly base. Skill-scaling (rather
    than a flat wage) sustains wealth dispersion -- otherwise everyone
    accumulates the same income and inequality washes out (gini -> 0). Income is
    exogenous (external wage), so total wealth grows; this is not a transfer.
    """
    active = pool.active_mask()
    factor = config.income_skill_min + (1.0 - config.income_skill_min) * 2.0 * pool.skill
    wage = config.base_income * np.clip(factor, 0.0, None)
    pool.wealth[active] += wage[active]
    return {"wage_paid": float(wage[active].sum())}


def update_price(
    price: float, demand: int, supply: int, config: EconomyConfig
) -> float:
    """Move the house price toward market balance (step 5: emergent pricing).

    ``demand`` is the number of houseless agents; ``supply`` is the number of
    available builders. The price drifts up when demand exceeds supply and down
    when supply exceeds demand, by at most ``price_adjust_speed`` per tick, and
    is clamped to [price_min, price_max].

        excess = (demand - supply) / (demand + supply)   # in [-1, 1]
        price *= 1 + price_adjust_speed * excess
    """
    total = demand + supply
    excess = (demand - supply) / total if total else 0.0
    new_price = price * (1.0 + config.price_adjust_speed * excess)
    return float(np.clip(new_price, config.price_min, config.price_max))


def attempt_builds(
    pool: AgentPool,
    config: EconomyConfig,
    rng: np.random.Generator,
    price: float | None = None,
) -> dict[str, object]:
    """Match builders to houseless occupants and attempt each build.

    Housing is universal: **every** active agent needs a house, builders
    included -- so a builder lives in a house that can decay and collapse just
    like anyone's. Builders are the suppliers; any houseless paying agent (of
    either role) is a candidate occupant. A builder cannot build their own house
    (self-pairs are dropped). Matching is non-spatial: each builder builds at
    most one house this tick, paired randomly.

    Each pair succeeds or fails on the builder's skill
    (``fail_prob = base_fail_rate + (1 - skill) * max_fail_rate``, so even a
    perfectly skilled builder fails at the irreducible floor). On **success** the
    occupant pays the fixed price to the builder (wealth-conserving), is housed,
    and the house inherits the builder's skill as its build quality. On
    **failure** nothing is transacted -- the (builder, occupant) pair is returned
    for the punishment layer; the occupant stays houseless and may retry.

    Returns
    -------
    {"houses_built": int,
     "failed_builders": np.ndarray[int],
     "failed_occupants": np.ndarray[int]}
    """
    if price is None:
        price = config.house_price
    empty = np.empty(0, dtype=np.int64)
    active = pool.active_mask()

    builders = np.flatnonzero(active & (pool.role == Role.BUILDER))
    occupants = np.flatnonzero(
        active & ~pool.has_house & (pool.wealth >= price)
    )

    n_builds = int(min(builders.size, occupants.size))
    if n_builds == 0:
        return {"houses_built": 0, "failed_builders": empty, "failed_occupants": empty}

    # Random pairing -- shuffle both pools and zip the first n_builds of each.
    rng.shuffle(builders)
    rng.shuffle(occupants)
    pair_builders = builders[:n_builds]
    pair_occupants = occupants[:n_builds]

    # A builder can't build their own house -- drop self-pairs (they retry).
    keep = pair_builders != pair_occupants
    pair_builders = pair_builders[keep]
    pair_occupants = pair_occupants[keep]

    fail_prob = np.clip(
        config.base_fail_rate
        + (1.0 - pool.skill[pair_builders]) * config.max_fail_rate,
        0.0,
        1.0,
    )
    failed = rng.random(pair_builders.size) < fail_prob
    succeeded = ~failed

    ok_builders = pair_builders[succeeded]
    ok_occupants = pair_occupants[succeeded]
    pool.wealth[ok_occupants] -= price
    pool.wealth[ok_builders] += price
    pool.has_house[ok_occupants] = True
    # The house inherits the builder's skill as its build quality (drives decay).
    pool.house_quality[ok_occupants] = pool.skill[ok_builders]

    return {
        "houses_built": int(succeeded.sum()),
        "failed_builders": pair_builders[failed],
        "failed_occupants": pair_occupants[failed],
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
