# Model cost ledger

An append-only record that motivates adding model complexity **only when it pays
for itself**. One row per model version in [`data/model_cost_log.csv`](data/model_cost_log.csv).

## The rule

```
total_cost = prediction_error + LAMBDA * n_mechanism_params
```

This is the **Minimum Description Length / Akaike (AIC)** idea: the best model
explains the real world most cheaply, paying a penalty for its own complexity.
A structural change is justified **only if it lowers `total_cost`** — i.e. the
error it removes outweighs the complexity it adds. This makes the project's
"complexity only when the data demands it" rule mechanical instead of a judgment
call.

## How each term is computed

- **`n_mechanism_params`** — the count of free *mechanism* parameters across
  `EconomyConfig`, `PunishmentConfig`, `ProfessionConfig` (auto-counted in
  `src/model_cost.py`). The **four founding seeds are deliberately excluded** —
  they are the model's fixed interface, not complexity. Adding a mechanism knob
  raises this; that is the cost of complexity.

- **`best_fit_error`** — the **best** the model can do, not a single run: over a
  coarse sweep of the seeds, the minimum relative error to each target metric,
  averaged across target countries. Using best-fit error measures the model's
  *structure* (what it can represent) rather than the luck of one seed setting.
  It is a coarse stand-in for full auto-calibration (build step 9), which will
  sharpen it. Today only **Gini** is compared (the one metric with a trusted
  real-world source — World Bank; see `data/countries.json`).

- **`LAMBDA`** — the exchange rate between the two terms, currently **0.02**.
  This is a **convention, not a law**: our error is a distance, not a
  log-likelihood, so AIC's principled penalty (2 per parameter, in nats) does
  not transfer directly. 0.02 was chosen so current complexity (~16 params →
  ~0.32) is comparable to current error (~0.35), so neither term trivially
  dominates. Re-tune as rows accumulate. The principled upgrade is to turn the
  comparator distance into a likelihood, which would yield LAMBDA for free.

## Caveats (so the ledger doesn't lie to us)

- The model's Gini is **wealth** inequality; the World Bank's is **income**
  inequality. The comparison is indicative until the model emits an income-Gini.
- `best_fit_error` is only as good as the seed sweep; a coarse grid can
  understate how well a model could fit. Sharpened by step 9 (calibration).

## Logging a new row

After any structural change, append a row:

```
.venv/bin/python scripts/log_model_cost.py --note "what changed"
```

The version is the short git hash, so each row is reproducible. Never edit or
delete existing rows — this is append-only, like `PROJECT_LOG.md`.
