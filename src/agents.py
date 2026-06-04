"""Agent population — structure-of-arrays layout.

We store the population as a set of parallel NumPy arrays (one array per
attribute) rather than a list of Agent objects. At N up to 100,000 this is the
difference between vectorised tick math and a Python-level loop, and it lets the
whole population be operated on with array ops. Index ``i`` is "agent i" across
every array.

Step 1 of the build order: agents merely exist and carry state. Income, housing,
failure, and punishment mechanics arrive in later steps.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

import numpy as np


class Role(IntEnum):
    """What an agent does. Stored as int8 in the population arrays."""

    BUILDER = 0
    RESIDENT = 1


class State(IntEnum):
    """An agent's status. Stored as int8 in the population arrays."""

    ACTIVE = 0
    IMPRISONED = 1
    DEAD = 2


@dataclass
class AgentPool:
    """The whole population as parallel arrays. All arrays share length N.

    Attributes
    ----------
    role : np.ndarray[int8]   -- Role enum value per agent
    state : np.ndarray[int8]  -- State enum value per agent
    skill : np.ndarray[float64] -- competence in [0, 1]
    wealth : np.ndarray[float64] -- accumulated wealth (currency-agnostic)
    has_house : np.ndarray[bool] -- whether the agent currently has a house
        (meaningful for residents; builders do not request housing)
    """

    role: np.ndarray
    state: np.ndarray
    skill: np.ndarray
    wealth: np.ndarray
    has_house: np.ndarray

    @property
    def n(self) -> int:
        return self.role.shape[0]

    @classmethod
    def create(
        cls,
        n: int,
        rng: np.random.Generator,
        *,
        skill_variance: float,
        initial_wealth: float = 100.0,
        builder_fraction: float = 0.5,
    ) -> "AgentPool":
        """Seed an initial population.

        skill is drawn from a normal centred at 0.5 with std ``skill_variance``,
        clipped to [0, 1] -- larger variance means a more unequal spread of
        competence (the README's sigma).

        The initial builder/resident split is a *placeholder*: profession
        distribution is meant to emerge from agents switching roles (build step
        4). Until then we seed a simple random split.
        """
        skill = np.clip(rng.normal(0.5, skill_variance, size=n), 0.0, 1.0)
        role = np.where(
            rng.random(n) < builder_fraction, Role.BUILDER, Role.RESIDENT
        ).astype(np.int8)
        state = np.full(n, State.ACTIVE, dtype=np.int8)
        wealth = np.full(n, float(initial_wealth), dtype=np.float64)
        has_house = np.zeros(n, dtype=bool)
        return cls(
            role=role, state=state, skill=skill, wealth=wealth, has_house=has_house
        )

    # --- convenience masks (handy for stats and, later, the tick loop) ---

    def active_mask(self) -> np.ndarray:
        return self.state == State.ACTIVE

    def alive_count(self) -> int:
        return int(np.count_nonzero(self.state != State.DEAD))

    def role_counts(self) -> dict[str, int]:
        """Count active agents by role (dead/imprisoned excluded)."""
        active = self.active_mask()
        return {
            "builders": int(np.count_nonzero(active & (self.role == Role.BUILDER))),
            "residents": int(np.count_nonzero(active & (self.role == Role.RESIDENT))),
        }

    def housed_resident_count(self) -> int:
        """Active residents that currently have a house."""
        active = self.active_mask()
        return int(
            np.count_nonzero(active & (self.role == Role.RESIDENT) & self.has_house)
        )
