"""Smoke script: build a small society and turn the loop.

Per the testing convention, simulation runs get a smoke script rather than
assertions: import the module, run a short simulation, exit 0 on success.

Run:  .venv/bin/python tests/smoke/smoke_tick_loop.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from simulation import FoundingParams, Simulation  # noqa: E402


def main() -> int:
    params = FoundingParams(
        population=1_000,
        skill_variance=0.15,
        risk_tolerance=0.5,
        punishment=0.5,
    )
    sim = Simulation(params, seed=42)

    print("seed params:", params)
    print("tick   0:", sim.summary())
    for t in (10, 25, 50):
        sim.run(t - sim.tick_count)
        print(f"tick {t:3d}:", sim.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
