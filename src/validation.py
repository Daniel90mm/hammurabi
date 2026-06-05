"""Country comparator: score a simulation's emergent metrics against targets.

This is the "data gate" from the project philosophy: a mechanism earns its place
only when the model can't match a real target without it. This module computes
the model's headline emergent metrics and a distance to a named target profile.

IMPORTANT: the bundled target profiles in data/countries.json are SYNTHETIC and
illustrative -- fabricating real country statistics is forbidden ("No
invention"). Replace them with sourced figures (and reconcile the unit mapping
between the model's abstract metrics and real-world statistics) before drawing
any real-world conclusions.
"""

from __future__ import annotations

import json
from pathlib import Path


def extract_metrics(sim) -> dict[str, float]:
    """The model's headline emergent metrics, as a comparable vector."""
    s = sim.summary()
    alive = max(int(s["alive"]), 1)
    population = max(int(sim.params.population), 1)
    return {
        "gini": float(s["gini"]),
        "builder_fraction": round(int(s["builders"]) / alive, 3),
        "affordability": float(s["affordability"]),
        "death_rate": round(int(s["dead"]) / population, 3),
    }


def score(
    metrics: dict[str, float],
    target: dict[str, float],
    weights: dict[str, float] | None = None,
) -> dict[str, object]:
    """Distance between a metric vector and a target (lower = better fit).

    Per-metric relative error |sim - target| / (|target| + eps), combined as a
    weighted mean. Keys starting with "_" (notes) and metrics absent from
    ``metrics`` are ignored.
    """
    errors: dict[str, float] = {}
    for key, tgt in target.items():
        if key.startswith("_") or key not in metrics:
            continue
        errors[key] = abs(metrics[key] - float(tgt)) / (abs(float(tgt)) + 1e-9)
    if not errors:
        return {"per_metric": {}, "distance": float("inf")}
    w = weights or {}
    wsum = sum(w.get(k, 1.0) for k in errors)
    distance = sum(w.get(k, 1.0) * e for k, e in errors.items()) / wsum
    return {
        "per_metric": {k: round(v, 4) for k, v in errors.items()},
        "distance": round(distance, 4),
    }


def load_targets(path: str | Path) -> dict[str, dict[str, float]]:
    """Load named target profiles from a JSON file (see data/countries.json)."""
    data = json.loads(Path(path).read_text())
    return data.get("profiles", {})


def best_fit(
    metrics: dict[str, float], targets: dict[str, dict[str, float]]
) -> tuple[str | None, dict[str, object]]:
    """Return the (profile name, score) with the smallest distance."""
    best_name, best = None, {"distance": float("inf")}
    for name, target in targets.items():
        result = score(metrics, target)
        if result["distance"] < best["distance"]:
            best_name, best = name, result
    return best_name, best
