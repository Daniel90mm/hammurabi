"""Offscreen frame rendering + the shared visual vocabulary.

This module is the single source of truth for *what the dashboard looks like*:
the colour palette, the per-agent colour rule, the formatted statistics lines,
and an offscreen Pillow renderer that draws a frame (map + stats) to a PNG.

Why offscreen rendering exists
------------------------------
Under a Wayland compositor, X11/Wayland screen-grabs of the live Tk window come
back black (XWayland windows aren't exposed to screen capture, and the
screencast portal is interactive). So to get a real picture of a frame -- for
verification, for an in-app "save snapshot", and eventually for the README's
PNG/GIF exports -- we redraw the frame ourselves from simulation state rather
than grabbing the screen. This is compositor-independent and deterministic.

The Tk dashboard imports the palette, ``agent_colors`` and ``stats_lines`` from
here so the two renderers never drift.
"""

from __future__ import annotations

import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from agents import AgentPool, Role, State

# --- palette (flat, terminal-like, high contrast) ---
BG = "#0a0a0a"
FG = "#e6e6e6"
DIM = "#6a6a6a"
ACCENT = "#5fd7ff"
HAIRLINE = "#2a2a2a"
ENTRY_BG = "#161616"

COLOR_BUILDER = "#5fd7ff"  # cyan
COLOR_RESIDENT = "#e6c84f"  # amber
COLOR_IMPRISONED = "#ff5f5f"  # red
COLOR_DEAD = "#3a3a3a"  # dim grey

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
    "house_price": "house price",
    "affordability": "affordability (price/wealth)",
    "cum_failures": "build failures",
    "cum_resident_deaths": "occupant deaths",
    "cum_builder_deaths": "builder deaths",
    "cum_to_builder": "→ builder",
    "cum_to_resident": "→ resident",
}

LEGEND = (
    ("builder", COLOR_BUILDER),
    ("resident", COLOR_RESIDENT),
    ("imprisoned", COLOR_IMPRISONED),
    ("dead", COLOR_DEAD),
)


def agent_colors(pool: AgentPool) -> np.ndarray:
    """Hex colour per agent; state takes priority over role."""
    colors = np.where(pool.role == Role.BUILDER, COLOR_BUILDER, COLOR_RESIDENT)
    colors = np.where(pool.state == State.IMPRISONED, COLOR_IMPRISONED, colors)
    colors = np.where(pool.state == State.DEAD, COLOR_DEAD, colors)
    return colors


def stats_lines(sim) -> list[str]:
    """The statistics panel as a list of monospace text lines.

    Builders/residents/housed get a percentage suffix; unknown summary keys are
    rendered generically, so new metrics appear automatically.
    """
    summary = sim.summary()
    p = sim.params
    lines = [
        f"seed pop={p.population}  σ={p.skill_variance}",
        f"ρ={p.risk_tolerance}  P={p.punishment}  seed={sim.seed}",
        "",
    ]
    width = max(len(STAT_LABELS.get(k, k)) for k in summary)
    active_roles = summary["builders"] + summary["residents"]

    def pct(x: float, denom: float) -> str:
        return f"{100 * x / denom:.1f}%" if denom else "—"

    for key, val in summary.items():
        label = STAT_LABELS.get(key, key)
        if key in ("builders", "residents"):
            lines.append(f"{label:<{width}}  {val:>6}  ({pct(val, active_roles)})")
        elif key == "housed":
            lines.append(
                f"{label:<{width}}  {val:>6}  ({pct(val, summary['residents'])})"
            )
        else:
            lines.append(f"{label:<{width}}  {val}")
    return lines


# --- font resolution ---


def _font_path(bold: bool = False) -> str | None:
    """Resolve a monospace TTF via fontconfig, with hard-coded fallbacks."""
    query = "monospace:bold" if bold else "monospace"
    try:
        out = subprocess.run(
            ["fc-match", "-f", "%{file}", query],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if out.returncode == 0 and out.stdout.strip().endswith((".ttf", ".otf")):
            return out.stdout.strip()
    except Exception:
        pass
    candidates = [
        "/usr/share/fonts/liberation-mono-fonts/LiberationMono-"
        + ("Bold" if bold else "Regular")
        + ".ttf",
        "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono"
        + ("-Bold" if bold else "")
        + ".ttf",
    ]
    for path in candidates:
        try:
            ImageFont.truetype(path, 12)
            return path
        except Exception:
            continue
    return None


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    path = _font_path(bold)
    if path:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


# --- offscreen frame renderer ---

PAD = 12
PIXEL = 4
TITLE_H = 26
STATUS_H = 22


def render_frame(
    sim,
    pos_x: np.ndarray,
    pos_y: np.ndarray,
    draw_idx: np.ndarray,
    size: tuple[int, int] = (960, 560),
) -> Image.Image:
    """Draw one frame (square city map + stats panel) to a Pillow image."""
    w, h = size
    im = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(im)

    f_title = _font(15, bold=True)
    f_body = _font(13)
    f_dim = _font(12)

    # map is a square filling the left column height
    map_side = h - TITLE_H - STATUS_H - PAD
    map_x, map_y = PAD, TITLE_H
    d.text((map_x, 6), "CITY — HAMMURABI", fill=ACCENT, font=f_title)
    d.rectangle(
        [map_x, map_y, map_x + map_side, map_y + map_side], outline=HAIRLINE
    )

    colors = agent_colors(sim.agents)
    span = map_side - PIXEL
    for i in draw_idx:
        x = map_x + pos_x[i] * span
        y = map_y + pos_y[i] * span
        d.rectangle([x, y, x + PIXEL, y + PIXEL], fill=colors[i])

    # stats panel
    sx = map_x + map_side + 18
    d.text((sx, 6), "STATISTICS", fill=ACCENT, font=f_title)
    ly = map_y
    for line in stats_lines(sim):
        d.text((sx, ly), line, fill=FG, font=f_body)
        ly += 20

    # legend
    ly += 8
    lx = sx
    for name, color in LEGEND:
        chip = f"■ {name}"
        d.text((lx, ly), chip, fill=color, font=f_dim)
        lx += d.textlength(chip, font=f_dim) + 16

    # status line
    d.text(
        (PAD, h - STATUS_H + 2),
        f"tick {sim.tick_count}",
        fill=DIM,
        font=f_dim,
    )
    return im


def save_screenshot(
    sim,
    path: str,
    pos_x: np.ndarray,
    pos_y: np.ndarray,
    draw_idx: np.ndarray,
    size: tuple[int, int] = (960, 560),
) -> str:
    """Render the current frame and write it to ``path``. Returns the path."""
    render_frame(sim, pos_x, pos_y, draw_idx, size).save(path)
    return path
