"""Profession switching: agents choose roles by profitability and risk (step 4).

Each tick, agents compare the mean wealth of the two roles and some switch
toward the more profitable one. Building is the *dangerous* trade (failure ->
punishment/death), so the founding parameter risk tolerance (rho) gates movement:

* builders richer  -> residents convert to builders, with prob scaled by  rho
  (only the risk-tolerant enter a dangerous, lucrative trade)
* residents richer -> builders flee to safety, with prob scaled by  (1 - rho)
  (the risk-averse abandon the dangerous trade faster)

A builder who switches to resident loses their house and re-enters the housing
market -- a feedback loop that renews building demand.

Mean *wealth* is a coarse profitability proxy (we don't track per-tick income
per agent); it works because builders accumulate the early building windfall.
A relative threshold + small switch rate damp oscillation.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from agents import AgentPool, Role


@dataclass(frozen=True)
class ProfessionConfig:
    base_switch_rate: float = 0.05  # per-tick switch probability before rho gating
    gap_threshold: float = 0.05  # min relative wealth gap before anyone switches


def switch_professions(
    pool: AgentPool,
    config: ProfessionConfig,
    risk_tolerance: float,
    rng: np.random.Generator,
) -> dict[str, int]:
    """Move some agents between roles based on the wealth gap. Mutates ``pool``."""
    stats = {"to_builder": 0, "to_resident": 0}
    active = pool.active_mask()
    builders = active & (pool.role == Role.BUILDER)
    residents = active & (pool.role == Role.RESIDENT)
    if not builders.any() or not residents.any():
        return stats  # need both roles present to compare

    b_mean = float(pool.wealth[builders].mean())
    r_mean = float(pool.wealth[residents].mean())

    if b_mean > r_mean * (1.0 + config.gap_threshold):
        # Building pays better: residents enter it, gated by risk tolerance.
        cand = np.flatnonzero(residents)
        p = config.base_switch_rate * risk_tolerance
        chosen = cand[rng.random(cand.size) < p]
        pool.role[chosen] = Role.BUILDER
        stats["to_builder"] = int(chosen.size)
    elif r_mean > b_mean * (1.0 + config.gap_threshold):
        # Building pays worse: builders flee to safety, gated by risk aversion.
        cand = np.flatnonzero(builders)
        p = config.base_switch_rate * (1.0 - risk_tolerance)
        chosen = cand[rng.random(cand.size) < p]
        pool.role[chosen] = Role.RESIDENT
        pool.has_house[chosen] = False  # re-enter the housing market
        stats["to_resident"] = int(chosen.size)

    return stats
