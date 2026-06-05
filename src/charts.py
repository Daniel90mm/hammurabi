"""Embedded live charts panel (matplotlib in Tk), styled flat-dark.

Sits beside/below the statistics text. Four charts that redraw from the sim's
per-tick history and current state:

    composition over time (line)   |   current split (pie)
    inequality / gini over time    |   wealth distribution (bar)

A row of toggles filters which series show on the composition chart -- the
first, minimal cut of "filterable". The matplotlib default look is overridden to
match DESIGN_PRINCIPLES: flat, dark, sharp, our palette, no chrome/toolbar.
"""

from __future__ import annotations

import tkinter as tk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from agents import State
from render import (
    ACCENT,
    BG,
    COLOR_BUILDER,
    COLOR_DEAD,
    COLOR_IMPRISONED,
    COLOR_RESIDENT,
    DIM,
    FG,
    HAIRLINE,
)

# Composition series shown on the time-line chart (key, label, colour).
SERIES = (
    ("builders", "builders", COLOR_BUILDER),
    ("residents", "residents", COLOR_RESIDENT),
    ("imprisoned", "imprisoned", COLOR_IMPRISONED),
    ("dead", "dead", COLOR_DEAD),
)


class ChartsPanel:
    """Owns the embedded figure and redraws it from a Simulation."""

    def __init__(self, parent: tk.Widget) -> None:
        # filter toggles for the composition chart
        toggles = tk.Frame(parent, bg=BG)
        toggles.pack(anchor="w", pady=(2, 0))
        tk.Label(toggles, text="show:", font=("monospace", 9), fg=DIM, bg=BG).pack(
            side="left", padx=(0, 4)
        )
        self.series_vars: dict[str, tk.BooleanVar] = {}
        for key, label, color in SERIES:
            var = tk.BooleanVar(value=True)
            self.series_vars[key] = var
            tk.Checkbutton(
                toggles,
                text=label,
                variable=var,
                command=self._on_toggle,
                font=("monospace", 9),
                fg=color,
                bg=BG,
                selectcolor=BG,
                activebackground=BG,
                activeforeground=color,
                highlightthickness=0,
                bd=0,
            ).pack(side="left", padx=(0, 6))

        self.fig = Figure(figsize=(5.2, 3.4), dpi=100, facecolor=BG)
        self.fig.subplots_adjust(
            left=0.10, right=0.97, top=0.90, bottom=0.10, hspace=0.55, wspace=0.30
        )
        self.ax_comp = self.fig.add_subplot(2, 2, 1)
        self.ax_pie = self.fig.add_subplot(2, 2, 2)
        self.ax_gini = self.fig.add_subplot(2, 2, 3)
        self.ax_wealth = self.fig.add_subplot(2, 2, 4)

        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, pady=(4, 0))
        self._sim = None  # remembered so a toggle can redraw without a new tick

    # --- styling ---

    def _style(self, ax, title: str) -> None:
        ax.set_facecolor(BG)
        ax.set_title(title, color=FG, fontsize=8, loc="left", pad=4)
        ax.tick_params(colors=DIM, labelsize=7, length=2)
        for side, spine in ax.spines.items():
            spine.set_visible(side in ("left", "bottom"))
            spine.set_color(HAIRLINE)

    # --- drawing ---

    def update(self, sim) -> None:
        self._sim = sim
        hist = list(sim.history)
        ticks = [h["tick"] for h in hist]

        # 1. composition over time (filtered)
        ax = self.ax_comp
        ax.clear()
        self._style(ax, "composition")
        for key, _label, color in SERIES:
            if self.series_vars[key].get():
                ax.plot(ticks, [h[key] for h in hist], color=color, linewidth=1.1)

        # 2. current split (pie)
        ax = self.ax_pie
        ax.clear()
        self._style(ax, "current split")
        ax.set_title("current split", color=FG, fontsize=8, loc="left", pad=4)
        s = sim.summary()
        vals = [s["builders"], s["residents"], s["imprisoned"], s["dead"]]
        colors = [COLOR_BUILDER, COLOR_RESIDENT, COLOR_IMPRISONED, COLOR_DEAD]
        keep = [(v, c) for v, c in zip(vals, colors) if v > 0]
        if keep:
            ax.pie(
                [v for v, _ in keep],
                colors=[c for _, c in keep],
                startangle=90,
                wedgeprops={"linewidth": 0.5, "edgecolor": BG},
            )

        # 3. inequality over time
        ax = self.ax_gini
        ax.clear()
        self._style(ax, "gini (inequality)")
        ax.plot(ticks, [h["gini"] for h in hist], color=ACCENT, linewidth=1.2)
        ax.set_ylim(0, 1)

        # 4. wealth distribution (bar/histogram of current active agents)
        ax = self.ax_wealth
        ax.clear()
        self._style(ax, "wealth distribution")
        active = sim.agents.state == State.ACTIVE
        wealth = sim.agents.wealth[active]
        if wealth.size:
            ax.hist(wealth, bins=24, color=COLOR_BUILDER)

        self.canvas.draw_idle()

    def _on_toggle(self) -> None:
        if self._sim is not None:
            self.update(self._sim)
