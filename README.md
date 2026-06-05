# hammurabi

**Agent-based society simulator that derives civilizational outcomes from first principles.**

Seed it with a society's founding parameters. Watch inequality, housing markets, and justice systems emerge — then score the result against real countries.

---

## The Idea

Babylon's Code of Hammurabi had a simple rule: if a builder's house collapses and kills the owner, the builder is put to death. Modern societies replaced this with fines, insurance, and prison time. But *why* did we converge on that? And what happens to a civilization that doesn't?

Hammurabi models societies as collections of agents who interact, fail, and face consequences. Different punishment regimes produce different emergent outcomes, and those outcomes are compared to real-world country statistics to validate the model. When the model *can't* match reality, the way it fails tells you what mechanism is missing.

## How It Works

### Founding Parameters (Seeds)

Every simulation is initialized with just 4 values:

| Parameter | What It Controls | Range |
|-----------|-----------------|-------|
| **Population** (N) | Scale of the society | 100 – 100,000 |
| **Skill variance** (σ) | How unequal agents are in competence | 0.01 – 0.5 |
| **Risk tolerance** (ρ) | Willingness to enter the dangerous building trade | 0.1 – 0.9 |
| **Punishment regime** (P) | Consequence for a fatal building failure | 0.0 – 1.0 |

Everything else — prices, profession distribution, inequality, who is housed — emerges from agent interactions.

> Are these the *right* four seeds? Maybe not — they may be too entangled. Finding a more orthogonal, minimal set is a data-driven question (sensitivity analysis + PCA) that needs more output metrics first; see *Future Directions* and `PROJECT_LOG.md`. `P` stays regardless — it is the thesis.

### Agents

Each agent has a role (builder or resident), a skill level, accumulated wealth, a state (active, imprisoned, or dead), and a house with a build quality. **Housing is universal** — every agent needs somewhere to live, *builders included*, so a builder's own home can collapse or wear out like anyone's. Each tick every active agent earns a **skill-scaled wage** (skilled agents earn more — this is what sustains inequality); builders additionally earn the house price when they build.

### The Tick Loop

```
for each tick:
    0. Released prisoners rejoin the active population
    1. House price updates from supply (builders) vs demand (houseless agents)
    2. Every active agent earns a skill-scaled wage
    3. Builders are matched to houseless agents and attempt a build;
       success depends on builder skill (with an irreducible failure floor)
    4. On a failed build: the occupant may be killed, and the builder is
       punished according to P (death / prison / fine)
    5. Agents compare recent role income; some switch profession (gated by ρ)
    6. Houses wear out — faster for shoddily-built ones — and owners re-enter
       the housing market
    7. The tick's statistics are recorded to the history buffer
```

### Punishment Spectrum

The punishment parameter `P` is continuous from 0 to 1, blended so it hits three anchors and interpolates smoothly between them:

- **P = 0.0** — Hammurabi regime: the builder is permanently removed (death)
- **P = 0.5** — Imprisonment: the builder is removed for a fixed number of ticks, then returns
- **P = 1.0** — Compensatory: the builder pays a fine and remains active

This explores the whole spectrum between ancient and modern justice, not just discrete categories.

## Running It

```bash
python3 -m venv .venv
.venv/bin/python -m pip install numpy matplotlib pillow pytest

# launch the GUI (batch-first: set seeds + run length, hit Run, read the result)
.venv/bin/python src/dashboard.py

# render a frame to PNG without a display (works under Wayland)
.venv/bin/python src/dashboard.py --screenshot out.png --ticks 200 --punishment 0.0

# refresh real-world targets, and append a model-cost ledger row
.venv/bin/python scripts/fetch_gini.py
.venv/bin/python scripts/log_model_cost.py --note "what changed"

# tests
.venv/bin/python -m pytest -q
```

A desktop launcher can be installed with `scripts/install-desktop.sh`.

## The Interface

A single flat, dark GUI window (Tkinter), **batch-first**: set the four seeds (0–1 sliders) and a run length, press **Run**, and the simulation runs to completion *instantly*. You then get:

- a **2D overhead map** of the city (each agent a colored pixel — cosmetic only; positions do not feed back into the model),
- a **statistics panel** (the focus),
- **live charts** from the run's history (composition over time, current split, Gini over time, wealth distribution),
- a **results verdict**: the run's income-Gini and the closest-matching real country.

Watching a run tick-by-tick is an optional toggle (`space`), not the default — the science is in running and comparing *many* runs, not watching one.

## What Gets Measured

Emergent properties read off each run:

- **Gini coefficient** — computed for both *wealth* and *income*. **Income-Gini is the metric scored against real data** (income inequality is what the World Bank reports).
- **Housing affordability** — house price / mean wealth (model units).
- **Profession ratio** — builder share of the active population.
- **Death rate** — cumulative deaths / initial population.

(*Builder turnover* and *shock recovery* are planned, not yet built.)

## Validation Against Real Countries

Each run is scored by a comparator (`src/validation.py`) against real **World Bank Gini coefficients** for a spread of countries (`data/countries.json`, refreshable via `scripts/fetch_gini.py`). Only Gini is compared today — it is the one model metric with a trusted real-world mapping; the others are intentionally *not* faked.

**Honest caveat:** the World Bank Gini is *income* inequality, while wealth-Gini and income-Gini differ — the model reports income-Gini for a like-for-like comparison, but the match remains indicative.

**Distinguishing "wrong parameters" from "wrong model":**
- If some seed combination reproduces reality, the structure is sound — you just need better parameter estimation.
- If *no* combination works (a full sweep), the model is structurally missing a mechanism, and the metric that fails tells you what to add.

### The model-cost ledger

Complexity is governed mechanically, not by taste, via an MDL/AIC-style rule:

```
total_cost = prediction_error + λ · (number of mechanism parameters)
```

A structural change is justified **only if it lowers `total_cost`** — the error it removes must outweigh the complexity it adds. Each model version appends one row to `data/model_cost_log.csv` (reproducible by git hash). See **`MODEL_COST.md`** for the full scheme and caveats. (It has already rejected one mechanism — wealth-returns raised the cost, so it was reverted on the record.)

## Output & Reproducibility

- Every run is reproducible from `(FoundingParams, seed)` — the layout and all randomness are seeded.
- Per-tick history is kept in memory (a bounded deque) and drives the charts.
- PNG snapshots of any frame: press `p` in the GUI, or use `--screenshot`.
- `data/countries.json` — real benchmark targets. `data/model_cost_log.csv` — the append-only cost ledger.
- A structured per-run output directory (`params.json`, plots, a story GIF) is planned.

## Tech Stack

- **Python** + **NumPy** — the simulation core (structure-of-arrays for scale).
- **Tkinter** (stdlib) — the GUI window (map + stats + charts).
- **Matplotlib** — the embedded live charts and static plots.
- **Pillow** — offscreen frame rendering (compositor-independent screenshots; the planned story GIF).
- **SciPy** — reserved for the planned auto-calibration optimizer.

## Project Structure

```
hammurabi/
  src/
    agents.py        # AgentPool: the population as parallel NumPy arrays
    economy.py       # wages, building, emergent pricing, decay
    punishment.py    # the P spectrum (death / prison / fine) + harm
    profession.py    # income-driven role switching, gated by ρ
    simulation.py    # FoundingParams + the tick loop + history buffer
    metrics.py       # pure emergent metrics (Gini)
    render.py        # palette, colour rules, offscreen PNG renderer
    charts.py        # embedded matplotlib charts panel
    dashboard.py     # the Tkinter GUI (batch-first run → results)
    validation.py    # country comparator (score vs real targets)
    model_cost.py    # complexity + error cost ledger machinery
  data/
    countries.json       # real World Bank Gini targets
    model_cost_log.csv   # append-only model-cost ledger
  scripts/           # launcher, icon, fetch_gini, log_model_cost
  tests/             # unit tests + tests/smoke/ run scripts
  MODEL_COST.md      # the complexity-vs-error rule
  PROJECT_LOG.md     # append-only decisions / findings / rejected ideas
  DESIGN_PRINCIPLES.md # hard UI rules
```

## Build Order & Status

The core simulation (the README's original steps 1–5) is complete, plus several mechanisms the data demanded:

- ✅ Agent data structures + tick loop
- ✅ Simple economy → **skill-scaled** income (sustains inequality)
- ✅ Failure + punishment mechanics (the `P` spectrum)
- ✅ Profession switching (driven by recent *income*, gated by ρ)
- ✅ Emergent supply/demand house pricing
- ✅ Housing **decay** (quality-dependent; renews demand so the sim never freezes)
- ✅ GUI (2D map + stats + charts), now **batch-first** ("run → results")
- ✅ Per-tick history buffer + Gini metrics
- ✅ Country comparator against real World Bank data
- ✅ Model-cost ledger (MDL/AIC complexity gate)
- ⏳ Story GIF replay; auto-calibration optimizer; structured run output

## Future Directions

Add only when the data demands it (the cost ledger is the referee).

### Population dynamics (the next coupled unit)
**Mortality + reproduction + inheritance.** Without births, population only declines to zero. Reproduction fixes that *and* enables wealth to concentrate across generations (dynasties) — the likely missing driver of *high* inequality, which one lifetime can't produce. Run length would then be expressed in **generations**. Lifespan/fertility are chosen for purpose (alive + multigenerational), not matched to real demographic numbers (there is no calendar here).

### Finding the right seeds
- **Sensitivity analysis** — which seed most affects which metric (reveals redundancy).
- **PCA on country statistics** — discover the orthogonal founding variables from data instead of guessing them. Both need more output metrics first.

### Additional roles & mechanisms (gated)
Architects, merchants, educators; education/mobility, insurance, reputation, taxation, corruption — each only when a real-world metric can't be reproduced without it.

### Scaling
100k+ agents may want Numba/C for hot loops; parameter sweeps are embarrassingly parallel.

## Philosophy

The goal is not to predict GDP or replicate a country exactly. It is to find the *simplest possible model* whose emergent properties qualitatively match real societies — and then ask what different justice systems do to civilizations over time.

Complexity is added only when the data demands it, and the cost ledger makes that rule mechanical. This is science, not feature creep.

## Inspiration

The [Code of Hammurabi](https://en.wikipedia.org/wiki/Code_of_Hammurabi) (c. 1750 BC), one of the oldest known written legal codes. The original stele is in the Louvre, Paris.

## License

MIT
