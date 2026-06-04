"""Failure consequences: the punishment spectrum driven by the P seed.

When a build fails (see economy.attempt_builds), two things happen: the occupant
may be harmed, and the builder is punished. The punishment regime is the
founding parameter P in [0, 1], mapped *continuously* onto the README's three
anchor points:

    P = 0.0  -> death        (Hammurabi: the builder is removed permanently)
    P = 0.5  -> imprisonment  (removed for prison_ticks, then returns)
    P = 1.0  -> compensatory  (pays a fine, stays active)

The blend (per failure, draw an outcome):

    death_prob  = max(0, 1 - 2P)     # 1 at P=0, 0 at P>=0.5
    fine_prob   = max(0, 2P - 1)     # 0 at P<=0.5, 1 at P=1
    prison_prob = 1 - death - fine   # peaks (=1) at P=0.5

This hits all three anchors exactly and interpolates smoothly between them.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from agents import AgentPool, State


@dataclass(frozen=True)
class PunishmentConfig:
    """Tunable knobs for failure consequences (not founding parameters)."""

    resident_death_prob: float = 0.30  # chance a collapse kills the occupant
    prison_ticks: int = 10  # sentence length for the imprisonment regime
    fine_amount: float = 150.0  # fine paid by the builder in the compensatory regime


def punishment_probs(p: float) -> tuple[float, float, float]:
    """Return (death_prob, prison_prob, fine_prob) for punishment regime ``p``."""
    death = max(0.0, 1.0 - 2.0 * p)
    fine = max(0.0, 2.0 * p - 1.0)
    prison = 1.0 - death - fine
    return death, prison, fine


def apply_failures(
    pool: AgentPool,
    config: PunishmentConfig,
    punishment: float,
    rng: np.random.Generator,
    failed_builders: np.ndarray,
    failed_occupants: np.ndarray,
) -> dict[str, int]:
    """Apply harm + punishment for a batch of failed builds. Mutates ``pool``.

    ``failed_builders[i]`` built the house that failed for ``failed_occupants[i]``.
    The occupant may be of either role (housing is universal).
    """
    # "resident_deaths" is the legacy key name; it counts occupant deaths of
    # either role (the GUI already labels it "occupant deaths").
    stats = {
        "resident_deaths": 0,
        "builder_deaths": 0,
        "imprisonments": 0,
        "fines": 0,
    }
    n = failed_builders.size
    if n == 0:
        return stats

    # 1. Occupant harm roll -- the collapse may kill the occupant.
    killed = rng.random(n) < config.resident_death_prob
    dead_occupants = failed_occupants[killed]
    pool.state[dead_occupants] = State.DEAD
    stats["resident_deaths"] = int(killed.sum())

    # 2. Builder punishment, drawn per failure from the P-blend.
    death_p, prison_p, _ = punishment_probs(punishment)
    roll = rng.random(n)
    death_mask = roll < death_p
    prison_mask = (roll >= death_p) & (roll < death_p + prison_p)
    fine_mask = ~death_mask & ~prison_mask

    b_death = failed_builders[death_mask]
    pool.state[b_death] = State.DEAD
    stats["builder_deaths"] = int(death_mask.sum())

    b_prison = failed_builders[prison_mask]
    pool.state[b_prison] = State.IMPRISONED
    pool.prison_remaining[b_prison] = config.prison_ticks
    stats["imprisonments"] = int(prison_mask.sum())

    b_fine = failed_builders[fine_mask]
    # Pay only what the builder has (no debt for now). The fine is removed from
    # the builder; routing it to the occupant as compensation is a later-step
    # refinement.
    paid = np.minimum(pool.wealth[b_fine], config.fine_amount)
    pool.wealth[b_fine] -= paid
    stats["fines"] = int(fine_mask.sum())

    return stats


def tick_prisons(pool: AgentPool) -> int:
    """Advance imprisonment by one tick; release builders whose sentence ends.

    Returns the number released this tick.
    """
    imprisoned = pool.state == State.IMPRISONED
    pool.prison_remaining[imprisoned] -= 1
    released = imprisoned & (pool.prison_remaining <= 0)
    pool.state[released] = State.ACTIVE
    pool.prison_remaining[released] = 0
    return int(released.sum())
