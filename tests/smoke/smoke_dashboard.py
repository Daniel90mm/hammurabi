"""Smoke script: build the dashboard, render a few frames, exit 0.

Does not call mainloop (that would block). Renders an initial frame, advances a
few ticks redrawing each time, then tears the window down. Skips gracefully with
exit 0 if there is no display (headless CI).

Run:  .venv/bin/python tests/smoke/smoke_dashboard.py
"""

import sys
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from dashboard import Dashboard  # noqa: E402
from simulation import FoundingParams, Simulation  # noqa: E402


def main() -> int:
    params = FoundingParams(
        population=1_000,
        skill_variance=0.15,
        risk_tolerance=0.5,
        punishment=0.5,
    )
    sim = Simulation(params, seed=42)

    try:
        dash = Dashboard(sim, tick_ms=50)
    except tk.TclError as exc:
        # Only skip when there is genuinely no display -- any other TclError is a
        # real bug (e.g. a bad widget option) and must fail loudly.
        msg = str(exc).lower()
        if "display" in msg or "no such file" in msg:
            print(f"no display ({exc}); skipping dashboard smoke")
            return 0
        raise

    dash._render_frame()
    dash.root.update()
    for _ in range(10):
        dash._advance()
        dash.root.update()
    print("dashboard rendered 11 frames:", sim.summary())
    dash.root.destroy()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
