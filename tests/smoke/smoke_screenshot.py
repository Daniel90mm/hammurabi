"""Smoke script: render a frame to a PNG via the offscreen renderer.

Verifies the compositor-independent screenshot path works end to end. Writes to
a temp file and checks it is a non-trivial PNG.

Run:  .venv/bin/python tests/smoke/smoke_screenshot.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from dashboard import make_positions  # noqa: E402
from render import save_screenshot  # noqa: E402
from simulation import FoundingParams, Simulation  # noqa: E402


def main() -> int:
    sim = Simulation(FoundingParams(1_500, 0.15, 0.5, 0.0), seed=42)
    sim.run(40)
    pos_x, pos_y, draw_idx = make_positions(sim)

    out = Path(tempfile.gettempdir()) / "hammurabi_smoke_frame.png"
    save_screenshot(sim, str(out), pos_x, pos_y, draw_idx)
    size = out.stat().st_size
    print(f"rendered {out} ({size} bytes) at tick {sim.tick_count}")
    assert size > 2_000, "PNG suspiciously small -- render likely blank"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
