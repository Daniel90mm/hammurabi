"""Smoke script: sweep founding parameters and print final headline stats.

Useful for eyeballing what each seed currently affects. As of build step 2 the
economy is inert (see PROJECT_LOG), so expect only `population` to move the
numbers -- skill_variance/risk_tolerance/punishment are dormant until steps 3-4.
This script is the place to re-check that as later steps wake those seeds up.

Run:  .venv/bin/python tests/smoke/smoke_param_sweep.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from simulation import FoundingParams, Simulation  # noqa: E402

N_TICKS = 50

# (label, population, skill_variance, risk_tolerance, punishment)
CASES = [
    ("baseline      ", 1_000, 0.15, 0.5, 0.5),
    ("small pop      ", 200, 0.15, 0.5, 0.5),
    ("large pop      ", 5_000, 0.15, 0.5, 0.5),
    ("low skill var  ", 1_000, 0.05, 0.5, 0.5),
    ("high skill var ", 1_000, 0.40, 0.5, 0.5),
    ("hammurabi P=0  ", 1_000, 0.15, 0.5, 0.0),
    ("compensatory P1", 1_000, 0.15, 0.5, 1.0),
]


def main() -> int:
    header = f"{'case':<16} {'alive':>6} {'builders':>9} {'residents':>10} {'housed':>7} {'mean_w':>8}"
    print(header)
    print("-" * len(header))
    for label, pop, sigma, rho, pun in CASES:
        params = FoundingParams(
            population=pop,
            skill_variance=sigma,
            risk_tolerance=rho,
            punishment=pun,
        )
        sim = Simulation(params, seed=42)
        sim.run(N_TICKS)
        s = sim.summary()
        print(
            f"{label:<16} {s['alive']:>6} {s['builders']:>9} "
            f"{s['residents']:>10} {s['housed']:>7} {s['mean_wealth']:>8}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
