#!/usr/bin/env python3
"""Download the Elexon datasets used by the app and save them as CSV snapshots.

    python backend/scripts/fetch_data.py

Writes data/wind_actuals.csv (FUELHH, WIND) and data/wind_forecasts.csv (WINDFOR).

Scope: decisions made in January 2026 -> delivery days 2 Jan .. 1 Feb 2026.
Forecasts are kept only when their lead time is <= --max-horizon hours to keep the file small
(the decision window is ~15-39 h, so 72 h leaves room for the lead-time analysis).
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
OUT = Path(__file__).resolve().parents[2] / "data"
UTC = timezone.utc


def get_json(url: str, params: dict, retries: int = 4):
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=90)
            r.raise_for_status()
            payload = r.json()
            return payload["data"] if isinstance(payload, dict) and "data" in payload else payload
        except Exception as exc:  # noqa: BLE001
            wait = 2**attempt
            print(f"  ! {exc} (retry in {wait}s)", file=sys.stderr)
            time.sleep(wait)
    raise SystemExit(f"Failed to fetch {url} {params}")


def chunks(start: datetime, end: datetime, step: timedelta):
    cur = start
    while cur < end:
        yield cur, min(cur + step, end)
        cur += step


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_actuals(start: datetime, end: datetime) -> pd.DataFrame:
    rows = []
    for a, b in chunks(start, end, timedelta(days=7)):
        print(f"FUELHH {a.date()} -> {b.date()}")
        rows += get_json(
            f"{BASE}/FUELHH/stream",
            {
                "settlementDateFrom": a.date().isoformat(),
                "settlementDateTo": (b - timedelta(days=1)).date().isoformat(),
                "fuelType": "WIND",
            },
        )
    df = pd.DataFrame(rows)
    df = df[df["fuelType"] == "WIND"][["startTime", "generation"]]
    return df.drop_duplicates("startTime", keep="last").sort_values("startTime")


def fetch_forecasts(pub_from: datetime, pub_to: datetime, max_horizon_h: int) -> pd.DataFrame:
    rows = []
    for a, b in chunks(pub_from, pub_to, timedelta(days=1)):
        print(f"WINDFOR published {a.date()}")
        rows += get_json(f"{BASE}/WINDFOR/stream", {"publishDateTimeFrom": iso(a), "publishDateTimeTo": iso(b)})
    df = pd.DataFrame(rows)[["startTime", "publishTime", "generation"]]
    lead = (pd.to_datetime(df["startTime"], utc=True) - pd.to_datetime(df["publishTime"], utc=True)).dt.total_seconds() / 3600
    df = df[(lead >= 0) & (lead <= max_horizon_h)]
    return df.drop_duplicates(["startTime", "publishTime"], keep="last").sort_values(["startTime", "publishTime"])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--max-horizon", type=int, default=72, help="max forecast lead time (hours) to keep")
    args = p.parse_args()

    OUT.mkdir(exist_ok=True)
    # Delivery days 2 Jan .. 1 Feb 2026 (UTC == London in winter). Fetch a little extra either side.
    act = fetch_actuals(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 2, 3, tzinfo=UTC))
    act.to_csv(OUT / "wind_actuals.csv", index=False)
    print(f"Saved {len(act)} actual rows")

    fc = fetch_forecasts(datetime(2025, 12, 29, tzinfo=UTC), datetime(2026, 2, 2, tzinfo=UTC), args.max_horizon)
    fc.to_csv(OUT / "wind_forecasts.csv", index=False)
    print(f"Saved {len(fc)} forecast rows")


if __name__ == "__main__":
    main()
