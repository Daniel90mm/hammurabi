"""Append one row to the model cost ledger (data/model_cost_log.csv).

Computes the current model's complexity + best-fit prediction error against the
real targets in data/countries.json and appends a reproducible row. Never
rewrites existing rows -- the ledger is append-only (see MODEL_COST.md).

Run:  .venv/bin/python scripts/log_model_cost.py --note "what changed"
"""

import argparse
import csv
import datetime as dt
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from model_cost import LAMBDA, best_fit_error, count_mechanism_params, total_cost  # noqa: E402
from validation import load_targets  # noqa: E402

LEDGER = ROOT / "data" / "model_cost_log.csv"
HEADER = [
    "version",
    "date",
    "n_mechanism_params",
    "best_fit_error",
    "lambda",
    "total_cost",
    "notes",
]


def git_version() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Append a row to the model cost ledger")
    ap.add_argument("--note", default="", help="what changed in this model version")
    ap.add_argument("--version", default=None, help="override the version label")
    args = ap.parse_args(argv)

    n_params = count_mechanism_params()
    error = best_fit_error(load_targets(ROOT / "data" / "countries.json"))
    cost = total_cost(error, n_params)
    row = {
        "version": args.version or git_version(),
        "date": dt.date.today().isoformat(),
        "n_mechanism_params": n_params,
        "best_fit_error": round(error, 4),
        "lambda": LAMBDA,
        "total_cost": round(cost, 4),
        "notes": args.note,
    }

    new_file = not LEDGER.exists()
    with LEDGER.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)
        if new_file:
            writer.writeheader()
        writer.writerow(row)

    print(f"appended row to {LEDGER}:")
    for k in HEADER:
        print(f"  {k:20} {row[k]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
