# NAVIGATION — hammurabi

Where everything lives.

## Directories

| Path | Purpose |
|------|---------|
| `src/` | Simulation source code (agents, economy, punishment, dashboard, etc.) |
| `tests/` | Unit tests for pure functions |
| `tests/smoke/` | Smoke scripts for simulation runs and exploratory mechanics |
| `docs/` | Human-written reference docs (mechanics, economy, punishment, etc.) |
| `data/` | Real-world benchmark data (country statistics) |
| `scripts/` | Automation utilities |
| `consults/` | Consult documents (LLM-to-LLM, written when stuck) |
| `handoffs/` | Session handoff documents |
| `runs/` | Simulation output (gitignored) |

## Root files

| File | Purpose |
|------|---------|
| `README.md` | Project overview, founding parameters, tick loop, tech stack |
| `CLAUDE.md` | Agent instructions (skill-agnostic port) |
| `AGENTS.md` | Agent instructions (mirror of CLAUDE.md) |
| `PROJECT_LOG.md` | Append-only record of ideas, decisions, findings, rejected concepts |
| `DESIGN_PRINCIPLES.md` | Hard UI/visualization rules (GUI window: 2D map + stats dashboard) |
| `pyproject.toml` | Project metadata, dependencies (numpy core; viz/calibration/dev extras), pytest config |
