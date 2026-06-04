"""Unit tests for the shared render layer (colour + stats formatting)."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agents import AgentPool, Role, State  # noqa: E402
from render import (  # noqa: E402
    COLOR_BUILDER,
    COLOR_DEAD,
    COLOR_IMPRISONED,
    COLOR_RESIDENT,
    agent_colors,
    stats_lines,
)
from simulation import FoundingParams, Simulation  # noqa: E402


def test_agent_colors_state_overrides_role():
    pool = AgentPool(
        role=np.array([Role.BUILDER, Role.RESIDENT, Role.BUILDER, Role.RESIDENT], np.int8),
        state=np.array([State.ACTIVE, State.ACTIVE, State.IMPRISONED, State.DEAD], np.int8),
        skill=np.full(4, 0.5),
        wealth=np.full(4, 100.0),
        has_house=np.zeros(4, bool),
        prison_remaining=np.zeros(4, np.int32),
        house_quality=np.zeros(4, np.float64),
    )
    colors = list(agent_colors(pool))
    assert colors[0] == COLOR_BUILDER
    assert colors[1] == COLOR_RESIDENT
    assert colors[2] == COLOR_IMPRISONED  # state beats role
    assert colors[3] == COLOR_DEAD


def test_stats_lines_includes_percentages_and_seeds():
    sim = Simulation(FoundingParams(1000, 0.15, 0.5, 0.5), seed=7)
    sim.run(5)
    text = "\n".join(stats_lines(sim))
    assert "seed pop=1000" in text
    assert "P=0.5" in text
    assert "%" in text  # builder/resident percentages present
    assert "build failures" in text  # pretty label from STAT_LABELS
