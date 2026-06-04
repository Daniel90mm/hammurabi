"""Real-time GUI: a 2D city map beside a statistics dashboard (Tkinter).

Per DESIGN_PRINCIPLES: flat, sharp, high-contrast, monospace, dense; a single
window split into the city map (left) and the stats panel (right, the main
focus); redraws once per tick; keyboard-first.

Design notes for future additions
----------------------------------
* The map is COSMETIC. Agent positions live here in the dashboard, not in the
  model -- the simulation does not know where agents are. If the "data demands
  it" trigger ever fires (see PROJECT_LOG), positions move into the model and
  this layer just reads them.
* The stats panel renders whatever ``sim.summary()`` returns. Add a metric to
  the summary (gini, profession ratio, ...) and it shows up here automatically;
  give it a pretty name in STAT_LABELS if you like.
* ``MAX_DRAW`` subsamples the population for very large N so per-tick redraw
  stays cheap (the N=100k open thread).
* Map colouring is isolated in ``_agent_colors`` -- extend it to colour by
  wealth, draw houses, or paint territory later.

Run:  .venv/bin/python src/dashboard.py [--population N --punishment P ...]
"""

from __future__ import annotations

import argparse
import tkinter as tk

import numpy as np

from agents import Role, State
from simulation import FoundingParams, Simulation

# --- palette (flat, terminal-like, high contrast) ---
BG = "#0a0a0a"
FG = "#e6e6e6"
DIM = "#6a6a6a"
ACCENT = "#5fd7ff"
HAIRLINE = "#2a2a2a"

COLOR_BUILDER = "#5fd7ff"  # cyan
COLOR_RESIDENT = "#e6c84f"  # amber
COLOR_IMPRISONED = "#ff5f5f"  # red
COLOR_DEAD = "#3a3a3a"  # dim grey

FONT = ("monospace", 11)
FONT_BOLD = ("monospace", 11, "bold")
FONT_TITLE = ("monospace", 13, "bold")

MAP_PX = 520  # map canvas is square, MAP_PX x MAP_PX
STATS_W = 340
PIXEL = 4  # agent dot size in px
MAX_DRAW = 4000  # cap on agents drawn per frame (subsampled if exceeded)

# Pretty names for known summary keys; unknown keys fall back to the raw key.
STAT_LABELS = {
    "tick": "tick",
    "alive": "alive",
    "builders": "builders",
    "residents": "residents",
    "imprisoned": "imprisoned",
    "dead": "dead",
    "housed": "housed residents",
    "mean_wealth": "mean wealth",
    "cum_failures": "build failures",
    "cum_resident_deaths": "occupant deaths",
    "cum_builder_deaths": "builder deaths",
}


class Dashboard:
    """Owns the window, the cosmetic agent positions, and the render loop."""

    def __init__(self, sim: Simulation, tick_ms: int = 200) -> None:
        self.sim = sim
        self.tick_ms = tick_ms
        self.playing = False

        n = sim.agents.n
        # Cosmetic positions in [0, 1), generated once. Seeded off the sim so the
        # layout is reproducible alongside the run.
        rng = np.random.default_rng(sim.seed + 1)
        self.pos_x = rng.random(n)
        self.pos_y = rng.random(n)

        # Subsample indices for drawing if the population is large.
        if n > MAX_DRAW:
            self.draw_idx = rng.choice(n, size=MAX_DRAW, replace=False)
        else:
            self.draw_idx = np.arange(n)

        self._build_widgets()

    # --- widget construction ---

    def _build_widgets(self) -> None:
        self.root = tk.Tk()
        self.root.title("Hammurabi")
        self.root.configure(bg=BG)
        self.root.minsize(640, 400)

        # status / help line first, pinned to the bottom so it survives resizing.
        self.status = tk.Label(self.root, font=FONT, fg=DIM, bg=BG, anchor="w")
        self.status.pack(side="bottom", fill="x", padx=8, pady=(0, 6))

        root = tk.Frame(self.root, bg=BG)
        root.pack(fill="both", expand=True, padx=8, pady=8)

        # left: city map -- expands to fill available space
        left = tk.Frame(root, bg=BG)
        left.pack(side="left", fill="both", expand=True)
        tk.Label(left, text="CITY — HAMMURABI", font=FONT_TITLE, fg=ACCENT, bg=BG).pack(
            anchor="w"
        )
        self.canvas = tk.Canvas(
            left,
            width=MAP_PX,
            height=MAP_PX,
            bg=BG,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _e: self._draw_map())

        # right: stats dashboard (the main focus)
        right = tk.Frame(root, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))
        tk.Label(right, text="STATISTICS", font=FONT_TITLE, fg=ACCENT, bg=BG).pack(
            anchor="w"
        )
        self.stats = tk.Label(
            right,
            font=FONT,
            fg=FG,
            bg=BG,
            justify="left",
            anchor="nw",
        )
        self.stats.pack(anchor="nw", fill="both", expand=True, pady=(6, 0))

        # legend -- one colour-matched chip per agent category
        legend = tk.Frame(right, bg=BG)
        legend.pack(anchor="nw", pady=(8, 0))
        for name, color in (
            ("builder", COLOR_BUILDER),
            ("resident", COLOR_RESIDENT),
            ("imprisoned", COLOR_IMPRISONED),
            ("dead", COLOR_DEAD),
        ):
            tk.Label(
                legend, text=f"■ {name}", font=FONT, fg=color, bg=BG
            ).pack(side="left", padx=(0, 14))

    # --- rendering ---

    def _agent_colors(self) -> np.ndarray:
        """Colour per agent: state takes priority over role."""
        a = self.sim.agents
        colors = np.where(a.role == Role.BUILDER, COLOR_BUILDER, COLOR_RESIDENT)
        colors = np.where(a.state == State.IMPRISONED, COLOR_IMPRISONED, colors)
        colors = np.where(a.state == State.DEAD, COLOR_DEAD, colors)
        return colors

    def _draw_map(self) -> None:
        c = self.canvas
        c.delete("all")
        # Live canvas size so the map fills whatever space it's given (fullscreen
        # included). Before the first <Configure> winfo_* can read 1; fall back.
        w = c.winfo_width()
        h = c.winfo_height()
        if w <= 1 or h <= 1:
            w = h = MAP_PX
        # hairline border (sharp, 1px)
        c.create_rectangle(0, 0, w - 1, h - 1, outline=HAIRLINE)

        colors = self._agent_colors()
        for i in self.draw_idx:
            x = self.pos_x[i] * (w - PIXEL)
            y = self.pos_y[i] * (h - PIXEL)
            c.create_rectangle(
                x, y, x + PIXEL, y + PIXEL, fill=colors[i], outline=""
            )

    def _draw_stats(self) -> None:
        summary = self.sim.summary()
        p = self.sim.params
        lines = [
            f"seed pop={p.population}  σ={p.skill_variance}",
            f"ρ={p.risk_tolerance}  P={p.punishment}  seed={self.sim.seed}",
            "",
        ]
        width = max(len(STAT_LABELS.get(k, k)) for k in summary)
        active_roles = summary["builders"] + summary["residents"]

        def pct(x: float, denom: float) -> str:
            return f"{100 * x / denom:.1f}%" if denom else "—"

        for key, val in summary.items():
            label = STAT_LABELS.get(key, key)
            if key in ("builders", "residents"):
                row = f"{label:<{width}}  {val:>6}  ({pct(val, active_roles)})"
            elif key == "housed":
                row = f"{label:<{width}}  {val:>6}  ({pct(val, summary['residents'])})"
            else:
                row = f"{label:<{width}}  {val}"
            lines.append(row)
        self.stats.config(text="\n".join(lines))

    def _render_frame(self) -> None:
        self._draw_map()
        self._draw_stats()
        state = "▶ playing" if self.playing else "❚❚ paused"
        self.status.config(
            text=f"{state}   tick {self.sim.tick_count}   "
            f"[space] play/pause   [s] step   [+/-] speed ({self.tick_ms}ms)   [q] quit"
        )

    # --- loop / controls ---

    def _advance(self) -> None:
        self.sim.tick()
        self._render_frame()

    def _loop(self) -> None:
        if self.playing:
            self._advance()
        self.root.after(self.tick_ms, self._loop)

    def _toggle_play(self, _evt=None) -> None:
        self.playing = not self.playing
        self._render_frame()

    def _step(self, _evt=None) -> None:
        self.playing = False
        self._advance()

    def _faster(self, _evt=None) -> None:
        self.tick_ms = max(20, self.tick_ms - 40)
        self._render_frame()

    def _slower(self, _evt=None) -> None:
        self.tick_ms = min(2000, self.tick_ms + 40)
        self._render_frame()

    def run(self) -> None:
        self.root.bind("<space>", self._toggle_play)
        self.root.bind("<s>", self._step)
        # speed up: '+' (shifted) and the unshifted '=' key share the key cap,
        # plus the numeric keypad '+'.
        self.root.bind("<plus>", self._faster)
        self.root.bind("<equal>", self._faster)
        self.root.bind("<KP_Add>", self._faster)
        self.root.bind("<minus>", self._slower)
        self.root.bind("<KP_Subtract>", self._slower)
        self.root.bind("<q>", lambda _e: self.root.destroy())
        self.root.focus_force()  # ensure key events reach the window
        self._render_frame()
        self._loop()
        self.root.mainloop()


def _parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Hammurabi real-time dashboard")
    ap.add_argument("--population", type=int, default=1_000)
    ap.add_argument("--skill-variance", type=float, default=0.15)
    ap.add_argument("--risk-tolerance", type=float, default=0.5)
    ap.add_argument("--punishment", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--tick-ms", type=int, default=200)
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    params = FoundingParams(
        population=args.population,
        skill_variance=args.skill_variance,
        risk_tolerance=args.risk_tolerance,
        punishment=args.punishment,
    )
    sim = Simulation(params, seed=args.seed)
    Dashboard(sim, tick_ms=args.tick_ms).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
