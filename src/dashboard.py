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
import math
import tkinter as tk

import numpy as np

from render import (
    ACCENT,
    BG,
    COLOR_IMPRISONED,
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

# Map each seed parameter to/from a normalized 0-1 slider position. Population
# uses a log scale (it spans 100..100,000); the rest are linear over their range.
def _pop_to_real(t: float) -> int:
    return int(round(100 * (1000 ** t)))


def _pop_to_norm(v: float) -> float:
    return math.log(max(v, 100) / 100) / math.log(1000)


# key -> (label, to_real(t), to_norm(value), value formatter)
PARAM_NORM = {
    "population": ("pop", _pop_to_real, _pop_to_norm, lambda v: str(v)),
    "skill_variance": (
        "σ",
        lambda t: round(0.01 + t * 0.49, 3),
        lambda v: (v - 0.01) / 0.49,
        lambda v: f"{v:.3f}",
    ),
    "risk_tolerance": (
        "ρ",
        lambda t: round(0.1 + t * 0.8, 3),
        lambda v: (v - 0.1) / 0.8,
        lambda v: f"{v:.2f}",
    ),
    "punishment": ("P", lambda t: round(t, 3), lambda v: v, lambda v: f"{v:.2f}"),
}

# Short, non-load-bearing explainers for the seed fields (shown on ⓘ hover).
PARAM_HELP = {
    "population": "Population (N): number of agents.  range 100–100,000",
    "skill_variance": "Skill variance (σ): spread of builder competence.  range 0.01–0.5",
    "risk_tolerance": "Risk tolerance (ρ): willingness to enter the dangerous\n"
    "building trade. Higher → more builders.  range 0.1–0.9",
    "punishment": "Punishment regime (P): consequence for a fatal build.\n"
    "0 = death (Hammurabi)   0.5 = prison   1 = fine.  range 0.0–1.0",
}


class Tooltip:
    """A minimal flat hover tooltip. Appears instantly, no animation."""

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _evt=None) -> None:
        if self.tip is not None:
            return
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)  # no title bar / border
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(
            self.tip,
            text=self.text,
            font=FONT,
            fg=FG,
            bg=ENTRY_BG,
            justify="left",
            padx=8,
            pady=5,
            highlightthickness=1,
            highlightbackground=ACCENT,
        ).pack()

    def _hide(self, _evt=None) -> None:
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


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
            takefocus=1,
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _e: self._draw_map())
        # Clicking the map (or its title) pulls focus out of the seed fields so
        # the keyboard controls the simulation instead of typing into a field.
        self.canvas.bind("<Button-1>", lambda _e: self.canvas.focus_set())

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

    # --- seed controls (normalized 0-1 sliders) ---

    def _build_controls(self) -> None:
        bar = tk.Frame(self.root, bg=BG)
        bar.pack(side="top", fill="x", padx=8, pady=(8, 0))

        tk.Label(bar, text="SEED", font=FONT_BOLD, fg=ACCENT, bg=BG).pack(
            side="left", padx=(0, 4)
        )

        self.sliders: dict[str, tk.Scale] = {}
        self.value_labels: dict[str, tk.Label] = {}
        p = self.sim.params
        current = {
            "population": p.population,
            "skill_variance": p.skill_variance,
            "risk_tolerance": p.risk_tolerance,
            "punishment": p.punishment,
        }
        for key, (label, to_real, to_norm, fmt) in PARAM_NORM.items():
            self._build_slider(bar, key, label, to_real, to_norm, fmt, current[key])

        tk.Label(bar, text="seed", font=FONT, fg=DIM, bg=BG).pack(side="left", padx=(10, 2))
        self.seed_entry = self._entry(bar, str(self.sim.seed), width=5)

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
        ).pack(side="left", padx=(12, 0))

    def _build_slider(self, bar, key, label, to_real, to_norm, fmt, current_value):
        """One labelled 0-1 slider with a live real-value readout and ⓘ help."""
        cell = tk.Frame(bar, bg=BG)
        cell.pack(side="left", padx=(10, 0))

        head = tk.Frame(cell, bg=BG)
        head.pack(anchor="w")
        tk.Label(head, text=label, font=FONT, fg=DIM, bg=BG).pack(side="left")
        info = tk.Label(head, text="ⓘ", font=FONT, fg=DIM, bg=BG, cursor="question_arrow")
        info.pack(side="left", padx=(2, 6))
        Tooltip(info, PARAM_HELP[key])
        value = tk.Label(head, text=fmt(current_value), font=FONT_BOLD, fg=FG, bg=BG)
        value.pack(side="left")
        self.value_labels[key] = value

        slider = tk.Scale(
            cell,
            from_=0.0,
            to=1.0,
            resolution=0.001,
            orient="horizontal",
            showvalue=False,
            length=120,
            width=10,
            bg=BG,
            troughcolor=ENTRY_BG,
            activebackground=ACCENT,
            highlightthickness=0,
            bd=0,
            sliderrelief="flat",
            command=lambda t, k=key: self._on_slider(k, float(t)),
        )
        slider.set(min(1.0, max(0.0, to_norm(current_value))))
        slider.pack(anchor="w")
        self.sliders[key] = slider

    def _on_slider(self, key: str, t: float) -> None:
        _, to_real, _, fmt = PARAM_NORM[key]
        self.value_labels[key].config(text=fmt(to_real(t)))

    def _entry(self, parent: tk.Widget, value: str, width: int) -> tk.Entry:
        vcmd = (self.root.register(self._is_number), "%P")
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
            validate="key",
            validatecommand=vcmd,
        )
        e.insert(0, value)
        e.bind("<Return>", lambda _e: self._on_run())
        e.pack(side="left")
        return e

    @staticmethod
    def _is_number(proposed: str) -> bool:
        """Allow only numeric input in seed fields (blocks '+', letters, spaces)."""
        if proposed in ("", "-", ".", "-."):
            return True  # permit partial entry
        try:
            float(proposed)
            return True
        except ValueError:
            return False

    def _on_run(self) -> None:
        """Read the seed sliders, rebuild the simulation, start and redraw."""
        def real(key):
            return PARAM_NORM[key][1](self.sliders[key].get())

        try:
            params = FoundingParams(
                population=real("population"),
                skill_variance=real("skill_variance"),
                risk_tolerance=real("risk_tolerance"),
                punishment=real("punishment"),
            )
            seed = int(self.seed_entry.get())
        except ValueError as exc:
            self.status.config(fg=COLOR_IMPRISONED, text=f"bad parameter: {exc}")
            return

        # Reuse the existing model knobs; only the seeds change.
        self.sim = Simulation(
            params,
            seed=seed,
            economy=self.sim.economy,
            punishment=self.sim.punishment,
            profession=self.sim.profession,
        )
        self._gen_positions()
        self.playing = True  # Run starts the simulation immediately
        self.status.config(fg=DIM)
        self.canvas.focus_set()  # move focus out of the entry so keys control the sim
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
        if self._editing():
            return
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

    def _editing(self) -> bool:
        """True while a seed field has keyboard focus -- controls stand down so
        the user can type (and keys don't double as sim commands)."""
        return isinstance(self.root.focus_get(), tk.Entry)

    def _toggle_play(self, _evt=None) -> None:
        if self._editing():
            return
        self.playing = not self.playing
        self._render_frame()

    def _step(self, _evt=None) -> None:
        if self._editing():
            return
        self.playing = False
        self._advance()

    def _faster(self, _evt=None) -> None:
        if self._editing():
            return
        self.tick_ms = max(20, self.tick_ms - 40)
        self._render_frame()

    def _slower(self, _evt=None) -> None:
        if self._editing():
            return
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
        self.root.bind("<q>", self._quit)
        self.root.focus_force()
        self.canvas.focus_set()  # controls active by default; click a field to edit
        self._render_frame()
        self._loop()
        self.root.mainloop()

    def _quit(self, _evt=None) -> None:
        if self._editing():
            return
        self.root.destroy()


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
