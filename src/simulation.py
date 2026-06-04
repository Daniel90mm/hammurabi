"""Core simulation: founding parameters + the tick loop.

Step 1 of the build order: the loop turns and the population exists. The
economic mechanics (income, housing requests, matching, failure, punishment,
profession switching, decay) are deliberately absent here -- each later build
step slots into ``Simulation.tick`` where the README's loop is sketched.

Every run is reproducible from (FoundingParams, seed).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from agents import AgentPool
from economy import EconomyConfig, build_houses, earn_income


@dataclass(frozen=True)
class FoundingParams:
    """The four founding parameters every simulation is seeded with.

    Ranges follow the README. ``__post_init__`` rejects out-of-range seeds so a
    bad parameter fails loudly at construction rather than producing quietly
    meaningless output.
    """

    population: int  # N : 100 .. 100_000
    skill_variance: float  # sigma : 0.01 .. 0.5
    risk_tolerance: float  # rho : 0.1 .. 0.9
    punishment: float  # P : 0.0 .. 1.0

    def __post_init__(self) -> None:
        self._check("population", self.population, 100, 100_000)
        self._check("skill_variance", self.skill_variance, 0.01, 0.5)
        self._check("risk_tolerance", self.risk_tolerance, 0.1, 0.9)
        self._check("punishment", self.punishment, 0.0, 1.0)

    @staticmethod
    def _check(name: str, value: float, lo: float, hi: float) -> None:
        if not (lo <= value <= hi):
            raise ValueError(
                f"{name}={value!r} out of range [{lo}, {hi}]"
            )


class Simulation:
    """Holds the population and advances it one tick at a time."""

    def __init__(
        self,
        params: FoundingParams,
        seed: int = 0,
        economy: EconomyConfig | None = None,
    ) -> None:
        self.params = params
        self.seed = seed
        self.economy = economy or EconomyConfig()
        self.rng = np.random.default_rng(seed)
        self.tick_count = 0
        self.agents = AgentPool.create(
            params.population,
            self.rng,
            skill_variance=params.skill_variance,
        )

    def tick(self) -> None:
        """Advance the simulation by one tick.

        Build order for the body of this loop (README tick loop). Steps 1-3 are
        implemented (flat income + fixed-price building); the rest land in later
        build phases:

            1. Agents earn income                                    [step 2]
            2-3. Residents request houses; builders build them       [step 2]
                 (price is fixed for now; emerges from supply/demand in step 5)
            4. Each build succeeds or fails based on builder skill    [step 3]
            5. On failure: injury/death roll + punishment applied (P) [step 3]
            6. Agents evaluate professions and some switch roles      [step 4]
            7. Houses age and decay                                   [step 7]
            8. Statistics logged                                      [step 7]
        """
        earn_income(self.agents, self.economy)
        build_houses(self.agents, self.economy, self.rng)
        self.tick_count += 1

    def run(self, n_ticks: int) -> None:
        """Advance ``n_ticks`` ticks."""
        for _ in range(n_ticks):
            self.tick()

    def summary(self) -> dict[str, object]:
        """A snapshot of headline numbers -- the seed of the future stats panel."""
        active = self.agents.active_mask()
        mean_wealth = (
            float(self.agents.wealth[active].mean()) if active.any() else 0.0
        )
        return {
            "tick": self.tick_count,
            "alive": self.agents.alive_count(),
            **self.agents.role_counts(),
            "housed": self.agents.housed_resident_count(),
            "mean_wealth": round(mean_wealth, 1),
        }
