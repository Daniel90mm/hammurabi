"""Unit tests for the country comparator (machinery only; targets are synthetic)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from simulation import FoundingParams, Simulation  # noqa: E402
from validation import best_fit, extract_metrics, load_targets, score  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data" / "countries.json"


def test_extract_metrics_has_expected_keys():
    sim = Simulation(FoundingParams(1000, 0.15, 0.5, 0.5), seed=1)
    sim.run(20)
    m = extract_metrics(sim)
    assert set(m) == {"gini", "builder_fraction", "affordability", "death_rate"}
    assert 0.0 <= m["gini"] <= 1.0
    assert 0.0 <= m["builder_fraction"] <= 1.0


def test_score_zero_for_exact_match():
    target = {"gini": 0.3, "builder_fraction": 0.5}
    result = score({"gini": 0.3, "builder_fraction": 0.5}, target)
    assert result["distance"] == 0.0


def test_score_increases_with_deviation():
    target = {"gini": 0.3}
    close = score({"gini": 0.32}, target)["distance"]
    far = score({"gini": 0.6}, target)["distance"]
    assert far > close > 0.0


def test_score_ignores_note_keys():
    target = {"_note": "ignore me", "gini": 0.3}
    result = score({"gini": 0.3}, target)
    assert result["per_metric"] == {"gini": 0.0}


def test_load_targets_are_real_countries_with_gini():
    targets = load_targets(DATA)
    assert "denmark" in targets and "south_africa" in targets
    # Real World Bank Gini values, converted to 0-1.
    assert 0.0 < targets["denmark"]["gini"] < 1.0
    assert targets["south_africa"]["gini"] > targets["denmark"]["gini"]


def test_best_fit_picks_matching_country():
    targets = load_targets(DATA)
    # A model whose gini exactly matches Denmark should be closest to Denmark.
    name, result = best_fit({"gini": targets["denmark"]["gini"]}, targets)
    assert name == "denmark"
    assert result["distance"] == 0.0
