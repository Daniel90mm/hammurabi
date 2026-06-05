"""Unit tests for the model cost ledger machinery."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from model_cost import best_fit_error, count_mechanism_params, total_cost  # noqa: E402


def test_complexity_counts_mechanism_params_only():
    # 4 founding seeds are excluded by construction; this counts config knobs.
    n = count_mechanism_params()
    assert n >= 13  # economy(10) + punishment(3) + profession(3) currently
    assert isinstance(n, int)


def test_total_cost_combines_error_and_complexity():
    assert total_cost(error=0.5, n_params=10, lambda_=0.02) == 0.7
    assert total_cost(error=0.0, n_params=0, lambda_=0.02) == 0.0


def test_best_fit_error_runs_and_is_nonnegative():
    # tiny single-point grid + short run keeps the test fast
    grid = {"skill_variance": [0.4], "risk_tolerance": [0.5], "punishment": [0.5]}
    err = best_fit_error(
        {"x": {"gini": 0.3}}, population=400, ticks=20, grid=grid
    )
    assert err >= 0.0


def test_best_fit_error_zero_when_target_matches_a_swept_value():
    grid = {"skill_variance": [0.4], "risk_tolerance": [0.5], "punishment": [0.5]}
    # Run once to learn the model's gini, then use it as the target -> error 0.
    from simulation import FoundingParams, Simulation
    from validation import extract_metrics

    sim = Simulation(FoundingParams(400, 0.4, 0.5, 0.5), seed=1)
    sim.run(20)
    g = extract_metrics(sim)["gini"]
    err = best_fit_error({"x": {"gini": g}}, population=400, ticks=20, grid=grid)
    assert err == 0.0
