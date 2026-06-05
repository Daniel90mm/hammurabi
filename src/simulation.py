"""Core simulation: founding parameters + the tick loop.

Step 1 of the build order: the loop turns and the population exists. The
economic mechanics (income, housing requests, matching, failure, punishment,
profession switching, decay) are deliberately absent here -- each later build
step slots into ``Simulation.tick`` where the README's loop is sketched.

Every run is reproducible from (FoundingParams, seed).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np

from agents import AgentPool, Role
from metrics import gini
from economy import (
    EconomyConfig,
    apply_capital_returns,
    attempt_builds,
    decay_houses,
    earn_income,
    update_price,
)
from profession import ProfessionConfig, switch_professions
from punishment import PunishmentConfig, apply_failures, tick_prisons


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
        punishment: PunishmentConfig | None = None,
        profession: ProfessionConfig | None = None,
    ) -> None:
        self.params = params
        self.seed = seed
        self.economy = economy or EconomyConfig()
        self.punishment = punishment or PunishmentConfig()
        self.profession = profession or ProfessionConfig()
        self.rng = np.random.default_rng(seed)
        self.tick_count = 0
        self.price = self.economy.house_price  # emergent house price (step 5)
        # Smoothed recent income per role -- the profitability signal that drives
        # profession switching (income, not lifetime wealth).
        self.builder_income = self.economy.base_income
        self.resident_income = self.economy.base_income
        # Smoothed per-agent income (wage + building revenue) -- the basis for the
        # income-Gini, which is the like-for-like match to World Bank income Gini
        # (the wealth-Gini below double-counts lifetime accumulation).
        self.recent_income = np.zeros(params.population, dtype=np.float64)
        self.agents = AgentPool.create(
            params.population,
            self.rng,
            skill_variance=params.skill_variance,
        )
        # Cumulative tallies across the whole run.
        self.totals = {
            "build_failures": 0,
            "resident_deaths": 0,
            "builder_deaths": 0,
            "imprisonments": 0,
            "fines": 0,
            "to_builder": 0,
            "to_resident": 0,
        }
        # Per-tick history for charts and validation (bounded so long runs don't
        # grow without limit). Seed it with the initial (tick 0) snapshot.
        self.history: deque[dict] = deque(maxlen=10_000)
        self.history.append(self.summary())

    def tick(self) -> None:
        """Advance the simulation by one tick.

        Build order for the body of this loop (README tick loop). Steps 1-3 are
        implemented (flat income + fixed-price building); the rest land in later
        build phases:

            1. House price updates from supply/demand                 [step 5]
            2. Agents earn income                                    [step 2]
            3-4. Houseless agents request houses; builders build at    [step 2/3]
                 the current price; each succeeds or fails on skill
            5. On failure: occupant harm roll + punishment (P)        [step 3]
            (prisons advance; sentences end and builders return)      [step 3]
            6. Agents evaluate professions and some switch roles (ρ)   [step 4]
            7. Houses wear out; owners re-enter the housing market     [decay]
            8. Statistics logged                                      [step 7]
        """
        # Released prisoners rejoin the active pool before this tick's building.
        tick_prisons(self.agents)

        # Price emerges from market tightness: houseless demand vs builder supply.
        active = self.agents.active_mask()
        demand = int(np.count_nonzero(active & ~self.agents.has_house))
        supply = int(np.count_nonzero(active & (self.agents.role == Role.BUILDER)))
        self.price = update_price(self.price, demand, supply, self.economy)

        wage_info = earn_income(self.agents, self.economy)
        capital_income = apply_capital_returns(self.agents, self.economy)
        result = attempt_builds(self.agents, self.economy, self.rng, self.price)

        # Per-agent income this tick = wage + capital return + building revenue;
        # smoothed (reuses the profession income-smoothing alpha).
        income = wage_info["wage"] + capital_income
        income[result["paid_builders"]] += self.price
        a = self.profession.income_ema_alpha
        self.recent_income = (1 - a) * self.recent_income + a * income

        consequences = apply_failures(
            self.agents,
            self.punishment,
            self.params.punishment,
            self.rng,
            result["failed_builders"],
            result["failed_occupants"],
        )

        # Update the smoothed role-income signal from this tick's earnings.
        # A builder earns the base wage plus a share of building revenue; a
        # resident earns only the base wage.
        base = self.economy.base_income
        builder_now = base + result["houses_built"] * self.price / max(supply, 1)
        alpha = self.profession.income_ema_alpha
        self.builder_income = (1 - alpha) * self.builder_income + alpha * builder_now
        self.resident_income = (1 - alpha) * self.resident_income + alpha * base

        switches = switch_professions(
            self.agents,
            self.profession,
            self.params.risk_tolerance,
            self.builder_income,
            self.resident_income,
            self.rng,
        )

        decay_houses(self.agents, self.economy, self.rng)

        self.totals["build_failures"] += int(result["failed_builders"].size)
        for key, val in consequences.items():
            self.totals[key] += val
        for key, val in switches.items():
            self.totals[key] += val

        self.tick_count += 1
        self.history.append(self.summary())

    def run(self, n_ticks: int) -> None:
        """Advance ``n_ticks`` ticks."""
        for _ in range(n_ticks):
            self.tick()

    def summary(self) -> dict[str, object]:
        """A snapshot of headline numbers -- the seed of the future stats panel."""
        active = self.agents.active_mask()
        active_wealth = self.agents.wealth[active]
        mean_wealth = float(active_wealth.mean()) if active.any() else 0.0
        return {
            "tick": self.tick_count,
            "alive": self.agents.alive_count(),
            **self.agents.role_counts(),
            "imprisoned": self.agents.imprisoned_count(),
            "dead": self.agents.dead_count(),
            "housed": self.agents.housed_resident_count(),
            "mean_wealth": round(mean_wealth, 1),
            "gini": round(gini(active_wealth), 3),
            "income_gini": round(gini(self.recent_income[active]), 3),
            "house_price": round(self.price, 1),
            "affordability": round(self.price / mean_wealth, 4) if mean_wealth else 0.0,
            "cum_failures": self.totals["build_failures"],
            "cum_resident_deaths": self.totals["resident_deaths"],
            "cum_builder_deaths": self.totals["builder_deaths"],
            "cum_to_builder": self.totals["to_builder"],
            "cum_to_resident": self.totals["to_resident"],
        }
