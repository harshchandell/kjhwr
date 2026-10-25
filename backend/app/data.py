"""Data access layer: loads the two Elexon datasets from local CSV files.

Why CSV snapshots instead of live API calls?
  * Serverless hosts (Vercel) are stateless and have short timeouts.
  * The assignment is scoped to January 2026, so the data is a fixed, small set.
  * Results are reproducible and the app keeps working if Elexon is down.
`backend/scripts/fetch_data.py` creates the snapshots from the Elexon API.
"""
from __future__ import annotations

from functools import lru_cache

import pandas as pd

from .config import DATA_DIR


class DataNotFound(RuntimeError):
    pass


def _read(name: str) -> pd.DataFrame:
    path = DATA_DIR / name
    if not path.exists():
        raise DataNotFound(
            f"{path} not found. Run `python backend/scripts/fetch_data.py` to download the Elexon data."
        )
    return pd.read_csv(path)


@lru_cache(maxsize=1)
def load_actuals() -> pd.DataFrame:
    """FUELHH, fuelType == WIND. Columns: start_time (UTC), actual_mw."""
    df = _read("wind_actuals.csv")
    out = pd.DataFrame(
        {
            "start_time": pd.to_datetime(df["startTime"], utc=True),
            "actual_mw": pd.to_numeric(df["generation"], errors="coerce"),
        }
    )
    return out.drop_duplicates("start_time", keep="last").sort_values("start_time").reset_index(drop=True)


@lru_cache(maxsize=1)
def load_forecasts() -> pd.DataFrame:
    """WINDFOR. Columns: start_time, publish_time (both UTC), forecast_mw."""
    df = _read("wind_forecasts.csv")
    out = pd.DataFrame(
        {
            "start_time": pd.to_datetime(df["startTime"], utc=True),
            "publish_time": pd.to_datetime(df["publishTime"], utc=True),
            "forecast_mw": pd.to_numeric(df["generation"], errors="coerce"),
        }
    )
    out = out.dropna(subset=["forecast_mw"]).drop_duplicates(["start_time", "publish_time"], keep="last")
    return out.sort_values(["start_time", "publish_time"]).reset_index(drop=True)
