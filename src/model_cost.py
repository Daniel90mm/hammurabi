"""Model cost: complexity + prediction error (an MDL/AIC-style ledger).

Total cost = best_fit_error + LAMBDA * n_mechanism_params

The idea (Minimum Description Length / Akaike): the best model is the one that
explains the real data most cheaply, paying a penalty for its own complexity.
Complexity is added only when it *lowers* total cost. See MODEL_COST.md.

Two deliberate choices:
* Complexity counts only MECHANISM parameters (the config knobs), NOT the four
  founding seeds -- the seeds are the fixed model interface, not model fat.
* Prediction error is the BEST-FIT error over a seed sweep, so it measures what
  the model *can* represent (its structure), not the luck of one seed setting.
  This is a coarse stand-in for full auto-calibration (build step 9).

LAMBDA is a pragmatic exchange rate, not a law: our error is a distance, not a
log-likelihood, so AIC's principled penalty doesn't transfer directly. Re-tune
as the ledger fills. The principled upgrade is to turn the comparator distance
into a likelihood, which would yield LAMBDA for free.
"""

from __future__ import annotations

import dataclasses

from economy import EconomyConfig
from profession import ProfessionConfig
from punishment import PunishmentConfig
from simulation import FoundingParams, Simulation
from validation import extract_metrics

LAMBDA = 0.02  # cost per mechanism parameter (convention -- see module docstring)

# Coarse seed sweep for best-fit error (population fixed; it barely moves gini).
DEFAULT_GRID = {
    "skill_variance": [0.05, 0.25, 0.45],
    "risk_tolerance": [0.1, 0.5, 0.9],
    "punishment": [0.0, 0.5, 1.0],
}


def count_mechanism_params() -> int:
    """Number of free mechanism parameters across the model's configs.

    Excludes the four founding seeds by construction (they live in
    FoundingParams, not in these mechanism configs)."""
    configs = (EconomyConfig, PunishmentConfig, ProfessionConfig)
    return sum(len(dataclasses.fields(cfg)) for cfg in configs)


def best_fit_error(
    targets: dict[str, dict],
    *,
    metric: str = "gini",
    population: int = 2000,
    ticks: int = 150,
    seed: int = 1,
    grid: dict[str, list[float]] | None = None,
) -> float:
    """Mean over targets of the closest the model can get to each (relative err).

    For every seed combination in the sweep we run a sim and read ``metric``;
    for each target we take the minimum relative error to that metric, then
    average across targets. Lower = the model can better cover real societies.
    """
    grid = grid or DEFAULT_GRID
    values = []
    for sigma in grid["skill_variance"]:
        for rho in grid["risk_tolerance"]:
            for pun in grid["punishment"]:
                sim = Simulation(
                    FoundingParams(population, sigma, rho, pun), seed=seed
                )
                sim.run(ticks)
                values.append(extract_metrics(sim)[metric])

    errors = []
    for target in targets.values():
        if metric not in target:
            continue
        tgt = float(target[metric])
        errors.append(min(abs(v - tgt) / (abs(tgt) + 1e-9) for v in values))
    return sum(errors) / len(errors) if errors else float("inf")


def total_cost(error: float, n_params: int, lambda_: float = LAMBDA) -> float:
    """complexity + error, on one scale via the LAMBDA exchange rate."""
    return error + lambda_ * n_params
