"""Regenerate data/countries.json from the World Bank Gini index (SI.POV.GINI).

Pulls the most-recent-value-per-country for a fixed spread of countries and
writes them (converted from the 0-100 scale to 0-1) with source/caveat notes.
This keeps the bundled real data auditable and refreshable rather than a mystery.

Run:  .venv/bin/python scripts/fetch_gini.py
Network required. Uses curl (the World Bank API rejects urllib's user agent).
"""

import json
import subprocess
import time
from pathlib import Path

# iso3 -> display key. A spread from very equal to very unequal.
COUNTRIES = {
    "NOR": "norway",
    "DNK": "denmark",
    "FIN": "finland",
    "SVN": "slovenia",
    "JPN": "japan",
    "DEU": "germany",
    "GBR": "united_kingdom",
    "USA": "united_states",
    "COL": "colombia",
    "BRA": "brazil",
    "ZAF": "south_africa",
}

SOURCE = (
    "World Bank, Gini index (indicator SI.POV.GINI), most-recent-value-per-country "
    "via api.worldbank.org. The API reports a 0-100 scale; values here are converted "
    "to 0-1 (gini = value / 100). Regenerate with scripts/fetch_gini.py."
)
CAVEAT = (
    "Only 'gini' has a trusted real-world source. The model's gini measures WEALTH "
    "inequality, whereas the World Bank Gini measures INCOME/consumption inequality "
    "(typically lower than wealth inequality) -- so this comparison is indicative, "
    "not exact, until the model emits an income-based gini. The other model metrics "
    "(builder_fraction, affordability, death_rate) have no trusted mapping and are "
    "intentionally omitted rather than fabricated (No invention)."
)


def fetch(iso3: str, retries: int = 3) -> tuple[float, str] | None:
    url = (
        f"https://api.worldbank.org/v2/country/{iso3}"
        "/indicator/SI.POV.GINI?format=json&mrnev=1"
    )
    for attempt in range(retries):
        raw = subprocess.run(
            ["curl", "-s", url], capture_output=True, timeout=30
        ).stdout.decode("utf-8-sig")
        try:
            rec = json.loads(raw)[1][0]
            return round(rec["value"] / 100.0, 3), rec["date"]
        except (json.JSONDecodeError, IndexError, KeyError, TypeError):
            time.sleep(0.6)  # transient empty/rate-limited response -- retry
    return None


def main() -> int:
    profiles = {}
    for iso3, key in COUNTRIES.items():
        result = fetch(iso3)
        if result is None:
            print(f"  {iso3}: no data, skipped")
            continue
        gini, year = result
        profiles[key] = {"gini": gini, "_year": int(year)}
        print(f"  {key}: gini={gini} ({year})")
        time.sleep(0.4)  # be gentle on the API

    out = {"_source": SOURCE, "_caveat": CAVEAT, "profiles": profiles}
    path = Path(__file__).resolve().parents[1] / "data" / "countries.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {len(profiles)} countries to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
