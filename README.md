# hammurabi  

**Agent-based society simulator that derives civilizational outcomes from first principles.**

Seed it with a country's founding parameters. Watch inequality, housing markets, and justice systems emerge.

---

## The Idea

Babylon's Code of Hammurabi had a simple rule: if a builder's house collapses and kills the owner, the builder is put to death. Modern societies replaced this with fines, insurance, and prison time. But *why* did we converge on that? And what happens to a civilization that doesn't?

Hammurabi is a simulation that answers this by modeling societies as collections of agents who interact, fail, and face consequences. Different punishment regimes produce different emergent outcomes and those outcomes can be compared to real-world country statistics to validate the model.

## How It Works

### Founding Parameters (Seeds)

Every simulation is initialized with just 4 values:

| Parameter | What It Controls | Range |
|-----------|-----------------|-------|
| **Population** (N) | Scale of the society | 100 -- 100,000 |
| **Skill variance** (sigma) | How unequal agents are in competence | 0.01 -- 0.5 |
| **Risk tolerance** (rho) | Willingness to enter dangerous professions | 0.1 -- 0.9 |
| **Punishment regime** (P) | Consequences for failure (death to fines) | 0.0 -- 1.0 |

Everything else — prices, profession distribution, inequality, housing availability emerges from agent interactions. Nothing is hardcoded.

### Agents

Each agent has a role (builder or resident), a wealth score, a skill level, and a state (active, imprisoned, or dead). Agents earn income, request services, and sometimes things go wrong — not maliciously, just probabilistically.

### The Tick Loop

```
for each tick:
    1. Agents earn income based on role
    2. Residents request houses (if needed)
    3. Builders are matched to requests (price emerges from supply/demand)
    4. Each build succeeds or fails based on builder skill
    5. On failure: injury/death roll + punishment applied
    6. Agents evaluate professions and some switch roles
    7. Houses age and decay
    8. Statistics logged, ASCII dashboard updated
```

### Punishment Spectrum

The punishment parameter P is continuous from 0 to 1:

- **P = 0.0** — Hammurabi regime: builder is permanently removed (death)
- **P = 0.5** — Imprisonment: builder is removed for N ticks, then returns
- **P = 1.0** — Compensatory: builder pays fines, remains active

This allows exploring the entire spectrum between ancient and modern justice systems, not just discrete categories.

## Simulation Modes

### Manual Mode
Provide the 4 seed parameters, run the simulation, visually compare results to real-world benchmarks.

### Auto-Calibration Mode
Specify a target country. An optimizer sweeps parameter space to minimize the distance between simulation output and real-world statistics. Outputs best-fit parameters.

### Free-Run Mode
Let the model mathematically pick parameter values using optimization (grid search or gradient-based). Useful for exploring what parameter combinations produce stable civilizations.

## What Gets Measured

Emergent properties compared against real-world data:

- **Gini coefficient** — income/wealth inequality
- **Profession ratio** — builder-to-resident distribution
- **Housing affordability** — median house price / median income
- **Builder turnover** — how fast builders leave or are removed
- **Shock recovery** — ticks to stabilize after removing 10% of builders

## Validation Against Real Countries

The model can be seeded with parameters estimated from real-world statistics for well-documented countries. If the emergent properties qualitatively match the real country, the model captures something real. If they don't, the *type* of failure tells you what mechanism is missing.

**Distinguishing "wrong parameters" from "wrong model":**
- If some parameter combination reproduces reality, the model structure is sound — you just need better parameter estimation.
- If *no* parameter combination works (full sweep), the model is structurally missing a mechanism. The specific metric that fails tells you what to add next.

This is how complexity is introduced responsibly: the data demands it, not intuition.

## Output Structure

```
hammurabi/
  runs/
    run_001_denmark/
      params.json            # Seed parameters + model version + random seed
      summary.txt            # Final stats, benchmark comparison, fit error
      dashboard.gif          # ASCII visualization over time
      tick_log.csv           # Raw per-tick statistics
      plots/
        gini_over_time.png
        population_over_time.png
        profession_distribution.png
        housing_affordability.png
    run_002_us/
      ...
```

Every run is fully reproducible: `params.json` stores the random seed and model version.

## Tech Stack

- **Python** with **NumPy** for the simulation core 
- **Matplotlib** for plot generation
- **Pillow** for ASCII-to-GIF rendering
- **SciPy** for auto-calibration optimization (optional)
- No GUI — terminal ASCII dashboard for real-time monitoring

## Project Structure

```
hammurabi/
  src/
    simulation.py       # Core tick loop
    agents.py           # Agent data structures
    economy.py          # Transaction and pricing logic
    punishment.py       # Regime definitions
    calibration.py      # Parameter optimization and country fitting
    dashboard.py        # ASCII real-time display
    logger.py           # Run logging and stats export
    gif_renderer.py     # ASCII frame capture to GIF
  data/
    countries.json      # Real-world benchmark statistics
  runs/                 # Output directory (gitignored)
  README.md
```

## Build Order

The implementation is phased so the simulation is interesting at every stage:

1. Agent data structures + basic tick loop
2. Simple economy (flat income, fixed housing price)
3. Failure + punishment mechanics
4. Profession switching (agents choose roles based on profitability)
5. Supply/demand pricing (house prices emerge from the market)
6. ASCII dashboard + GIF capture
7. Logging + plot generation
8. Country benchmark data + comparison metrics
9. Auto-calibration mode (optimizer)
10. Model versioning for structural changes

**Steps 1--5** are the core simulation. **Steps 6--10** are infrastructure. Something interesting emerges by step 5.

## Future Directions

These are avenues to explore *after* the core model is validated:

### Additional Roles
- **Architects** (manage builders, increase success probability)
- **Merchants** (trade goods between agents)
- **Educators** (allow role transitions, raise skill levels)
- Roles should only be added when the model fails to reproduce a real-world metric without them

### Additional Mechanisms
- **Education system** — non-builders can train to become builders (role mobility)
- **Insurance markets** — agents pool risk by contributing to a shared fund
- **Reputation system** — agents prefer high-skill builders, creating market dynamics
- **Government / taxation** — redistribute wealth, fund public services
- **Corruption** — agents who circumvent rules for personal gain

### Advanced Validation
- **PCA on country statistics** — instead of hand-picking 4 seed parameters, use principal component analysis on real-world data to find the mathematically orthogonal founding variables
- **Evolutionary meta-layer** — let punishment parameters mutate across generations and see which justice systems survive natural selection
- **Sensitivity analysis** — which seed parameter has the largest effect on which emergent property?

### Scaling
- For 100k+ agents, hot loops can be rewritten in C or accelerated with Numba
- Parameter sweeps are embarrassingly parallel — can be distributed across cores

## Philosophy

The goal is not to predict GDP or replicate a country exactly. It is to find the *simplest possible model* whose emergent properties qualitatively match real societies, and then to ask: what do different justice systems do to civilizations over time?

Complexity is added only when the data demands it. If the model fails to match reality, the type of failure tells you what mechanism to add. This is science, not feature creep.

## Inspiration

The [Code of Hammurabi](https://en.wikipedia.org/wiki/Code_of_Hammurabi) (c. 1750 BC), one of the oldest known written legal codes. The original stele is in the Louvre, Paris.

## License

MIT