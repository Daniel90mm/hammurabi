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

from render import (
    ACCENT,
    BG,
    DIM,
    ENTRY_BG,
    FG,
    HAIRLINE,
    LEGEND,
    PIXEL,
    agent_colors,
    save_screenshot,
    stats_lines,
)
from simulation import FoundingParams, Simulation

# Tk-specific presentation (palette/colour logic live in render.py).
FONT = ("monospace", 11)
FONT_BOLD = ("monospace", 11, "bold")
FONT_TITLE = ("monospace", 13, "bold")

MAP_PX = 520  # initial map canvas size; it expands to fill the window
MAX_DRAW = 4000  # cap on agents drawn per frame (subsampled if exceeded)


def make_positions(sim: Simulation):
    """Cosmetic (x, y) positions + draw indices for a sim's population.

    Positions live in the visualization layer, not the model -- the sim doesn't
    know where agents are (cosmetic-first decision). Seeded off the sim seed so
    the layout is reproducible alongside the run; subsampled past MAX_DRAW.
    """
    n = sim.agents.n
    rng = np.random.default_rng(sim.seed + 1)
    pos_x = rng.random(n)
    pos_y = rng.random(n)
    if n > MAX_DRAW:
        draw_idx = rng.choice(n, size=MAX_DRAW, replace=False)
    else:
        draw_idx = np.arange(n)
    return pos_x, pos_y, draw_idx


class Dashboard:
    """Owns the window, the cosmetic agent positions, and the render loop."""

    def __init__(self, sim: Simulation, tick_ms: int = 200) -> None:
        self.sim = sim
        self.tick_ms = tick_ms
        self.playing = False
        self._gen_positions()
        self._build_widgets()

    def _gen_positions(self) -> None:
        self.pos_x, self.pos_y, self.draw_idx = make_positions(self.sim)

    # --- widget construction ---

    def _build_widgets(self) -> None:
        self.root = tk.Tk()
        self.root.title("Hammurabi")
        self.root.configure(bg=BG)
        self.root.minsize(640, 400)

        # status / help line first, pinned to the bottom so it survives resizing.
        self.status = tk.Label(self.root, font=FONT, fg=DIM, bg=BG, anchor="w")
        self.status.pack(side="bottom", fill="x", padx=8, pady=(0, 6))

        # seed-parameter control bar (inline edits, no modal) pinned to the top.
        self._build_controls()

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
        for name, color in LEGEND:
            tk.Label(
                legend, text=f"■ {name}", font=FONT, fg=color, bg=BG
            ).pack(side="left", padx=(0, 14))

    # --- seed controls ---

    # (field key, label, formatter) prefilled from the current run.
    _FIELDS = (
        ("population", "pop", lambda p: str(p.population)),
        ("skill_variance", "σ", lambda p: str(p.skill_variance)),
        ("risk_tolerance", "ρ", lambda p: str(p.risk_tolerance)),
        ("punishment", "P", lambda p: str(p.punishment)),
    )

    def _build_controls(self) -> None:
        bar = tk.Frame(self.root, bg=BG)
        bar.pack(side="top", fill="x", padx=8, pady=(8, 0))

        tk.Label(bar, text="SEED", font=FONT_BOLD, fg=ACCENT, bg=BG).pack(side="left")

        self.entries: dict[str, tk.Entry] = {}
        p = self.sim.params
        for key, label, fmt in self._FIELDS:
            tk.Label(bar, text=label, font=FONT, fg=DIM, bg=BG).pack(
                side="left", padx=(12, 2)
            )
            e = self._entry(bar, fmt(p), width=6)
            self.entries[key] = e

        tk.Label(bar, text="seed", font=FONT, fg=DIM, bg=BG).pack(side="left", padx=(12, 2))
        self.seed_entry = self._entry(bar, str(self.sim.seed), width=6)

        tk.Button(
            bar,
            text="▶ Run",
            font=FONT_BOLD,
            fg=BG,
            bg=ACCENT,
            activebackground=FG,
            relief="flat",
            bd=0,
            padx=10,
            command=self._on_run,
        ).pack(side="left", padx=(14, 0))

    def _entry(self, parent: tk.Widget, value: str, width: int) -> tk.Entry:
        e = tk.Entry(
            parent,
            width=width,
            font=FONT,
            fg=FG,
            bg=ENTRY_BG,
            insertbackground=FG,
            relief="flat",
            highlightthickness=1,
            highlightbackground=HAIRLINE,
            highlightcolor=ACCENT,
        )
        e.insert(0, value)
        e.bind("<Return>", lambda _e: self._on_run())
        e.pack(side="left")
        return e

    def _on_run(self) -> None:
        """Read the seed fields, rebuild the simulation, reset and redraw."""
        try:
            params = FoundingParams(
                population=int(self.entries["population"].get()),
                skill_variance=float(self.entries["skill_variance"].get()),
                risk_tolerance=float(self.entries["risk_tolerance"].get()),
                punishment=float(self.entries["punishment"].get()),
            )
            seed = int(self.seed_entry.get())
        except ValueError as exc:
            self.status.config(fg=COLOR_IMPRISONED, text=f"bad parameter: {exc}")
            return

        # Reuse the existing economy/punishment knobs; only the seeds change.
        self.sim = Simulation(
            params,
            seed=seed,
            economy=self.sim.economy,
            punishment=self.sim.punishment,
        )
        self._gen_positions()
        self.playing = False
        self.status.config(fg=DIM)
        self._render_frame()

    # --- rendering (colour + stats formatting come from render.py) ---

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

        colors = agent_colors(self.sim.agents)
        for i in self.draw_idx:
            x = self.pos_x[i] * (w - PIXEL)
            y = self.pos_y[i] * (h - PIXEL)
            c.create_rectangle(
                x, y, x + PIXEL, y + PIXEL, fill=colors[i], outline=""
            )

    def _draw_stats(self) -> None:
        self.stats.config(text="\n".join(stats_lines(self.sim)))

    def _render_frame(self) -> None:
        self._draw_map()
        self._draw_stats()
        state = "▶ playing" if self.playing else "❚❚ paused"
        self.status.config(
            fg=DIM,
            text=f"{state}   tick {self.sim.tick_count}   "
            f"[space] play/pause   [s] step   [+/-] speed ({self.tick_ms}ms)   "
            f"[p] snapshot   [q] quit",
        )

    def _snapshot(self, _evt=None) -> None:
        """Save a PNG of the current frame via the offscreen renderer.

        The live Tk window can't be screen-grabbed under Wayland, so we redraw
        the same frame to an image from simulation state instead.
        """
        path = f"hammurabi_t{self.sim.tick_count}_seed{self.sim.seed}.png"
        save_screenshot(self.sim, path, self.pos_x, self.pos_y, self.draw_idx)
        self.status.config(fg=ACCENT, text=f"saved snapshot -> {path}")

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
        self.root.bind("<p>", self._snapshot)
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
    ap.add_argument(
        "--screenshot",
        metavar="PATH",
        help="render a frame to PATH and exit (no GUI); use with --ticks",
    )
    ap.add_argument(
        "--ticks",
        type=int,
        default=0,
        help="ticks to advance before --screenshot",
    )
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

    if args.screenshot:
        # Headless render -- no Tk, works regardless of the compositor.
        sim.run(args.ticks)
        pos_x, pos_y, draw_idx = make_positions(sim)
        save_screenshot(sim, args.screenshot, pos_x, pos_y, draw_idx)
        print(f"saved {args.screenshot} at tick {sim.tick_count}")
        return 0

    Dashboard(sim, tick_ms=args.tick_ms).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
