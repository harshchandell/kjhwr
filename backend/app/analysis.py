"""Pure analysis functions (no I/O, no web framework) so they are easy to test.

Core idea
---------
WINDFOR holds MANY forecasts for each target half-hour (one per publishTime).
A buyer deciding on day D-1 can only use forecasts published up to their decision
cutoff, and should use the most recent of those. Picking the latest forecast
overall would leak information from after the decision and flatter accuracy.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd

from .config import LONDON

HORIZON_EDGES = [0, 6, 12, 18, 24, 30, 36, 42, 48, 60, 72]


#  time helpers
def _london_midnight_utc(d: date) -> pd.Timestamp:
    return pd.Timestamp(datetime.combine(d, time.min, tzinfo=LONDON)).tz_convert("UTC")


def cutoff_utc(decision_date: date, cutoff: time) -> pd.Timestamp:
    """Decision cutoff on day D-1 (London local time) expressed in UTC."""
    return pd.Timestamp(datetime.combine(decision_date, cutoff, tzinfo=LONDON)).tz_convert("UTC")


def delivery_window_utc(decision_date: date) -> tuple[pd.Timestamp, pd.Timestamp]:
    """[start, end) of the London-local delivery day (decision_date + 1)."""
    delivery = decision_date + timedelta(days=1)
    return _london_midnight_utc(delivery), _london_midnight_utc(delivery + timedelta(days=1))


# ------------------------------------------------------------ decision forecast
def decision_forecast(forecasts: pd.DataFrame, decision_date: date, cutoff: time) -> pd.DataFrame:
    """Latest forecast per half-hour of the delivery day that was published by the cutoff."""
    start, end = delivery_window_utc(decision_date)
    co = cutoff_utc(decision_date, cutoff)
    f = forecasts[
        (forecasts["start_time"] >= start) & (forecasts["start_time"] < end) & (forecasts["publish_time"] <= co)
    ]
    f = f.sort_values(["start_time", "publish_time"]).drop_duplicates("start_time", keep="last")
    return f.assign(decision_date=decision_date).reset_index(drop=True)


def build_evaluation_frame(
    forecasts: pd.DataFrame, actuals: pd.DataFrame, start: date, end: date, cutoff: time
) -> pd.DataFrame:
    """Decision-time forecast joined with actuals for every decision day in [start, end]."""
    parts = []
    d = start
    while d <= end:
        parts.append(decision_forecast(forecasts, d, cutoff))
        d += timedelta(days=1)
    parts = [p for p in parts if not p.empty]
    if not parts:
        return pd.DataFrame(columns=["start_time", "publish_time", "forecast_mw", "decision_date", "actual_mw", "error_mw"])
    df = pd.concat(parts, ignore_index=True).merge(actuals, on="start_time", how="left")
    df["error_mw"] = df["forecast_mw"] - df["actual_mw"]  # + = over-forecast (risk of under-buying)
    return df


# ---------------------------------------------------------------------- metrics
def metrics(df: pd.DataFrame) -> dict:
    """Accuracy metrics on rows that have both a forecast and an actual."""
    d = df.dropna(subset=["forecast_mw", "actual_mw"])
    n = len(d)
    if n == 0:
        return {"n": 0}
    err = d["error_mw"].to_numpy()
    abs_err = np.abs(err)
    mean_actual = float(d["actual_mw"].mean())
    return {
        "n": int(n),
        "mean_actual_mw": mean_actual,
        "mean_forecast_mw": float(d["forecast_mw"].mean()),
        "mae_mw": float(abs_err.mean()),
        "rmse_mw": float(np.sqrt((err**2).mean())),
        "bias_mw": float(err.mean()),
        "mae_pct_of_mean_actual": float(abs_err.mean() / mean_actual * 100) if mean_actual > 0 else None,
        "p90_abs_error_mw": float(np.quantile(abs_err, 0.90)),
        "p95_abs_error_mw": float(np.quantile(abs_err, 0.95)),
        "max_abs_error_mw": float(abs_err.max()),
        # 80% of half-hours fall between these two signed errors (forecast - actual)
        "error_p10_mw": float(np.quantile(err, 0.10)),
        "error_p90_mw": float(np.quantile(err, 0.90)),
        "over_forecast_share_pct": float((err > 0).mean() * 100),
    }


def daily_metrics(df: pd.DataFrame) -> list[dict]:
    rows = []
    for dd, g in df.groupby("decision_date"):
        m = metrics(g)
        m["decision_date"] = dd.isoformat()
        m["delivery_date"] = (dd + timedelta(days=1)).isoformat()
        rows.append(m)
    return rows


def hourly_metrics(df: pd.DataFrame) -> list[dict]:
    d = df.dropna(subset=["forecast_mw", "actual_mw"]).copy()
    if d.empty:
        return []
    d["hour"] = d["start_time"].dt.tz_convert(LONDON).dt.hour
    d["abs_error_mw"] = d["error_mw"].abs()
    g = d.groupby("hour").agg(mae_mw=("abs_error_mw", "mean"), bias_mw=("error_mw", "mean"), n=("error_mw", "size"))
    return [{"hour": int(h), **{k: float(v) for k, v in r.items()}} for h, r in g.iterrows()]


def error_histogram(df: pd.DataFrame, bins: int = 24) -> list[dict]:
    d = df.dropna(subset=["error_mw"])
    if d.empty:
        return []
    lim = float(np.ceil(np.quantile(np.abs(d["error_mw"]), 0.995) / 100) * 100) or 100.0
    counts, edges = np.histogram(d["error_mw"].clip(-lim, lim), bins=bins, range=(-lim, lim))
    return [
        {"from_mw": float(edges[i]), "to_mw": float(edges[i + 1]), "mid_mw": float((edges[i] + edges[i + 1]) / 2), "count": int(c)}
        for i, c in enumerate(counts)
    ]


# ---------------------------------------------------------------- lead-time view
def horizon_metrics(forecasts: pd.DataFrame, actuals: pd.DataFrame, start: date, end: date) -> list[dict]:
    """Accuracy of ALL published forecasts grouped by lead time (startTime - publishTime).

    Delivery days covered: decision dates in [start, end] + 1 day.
    """
    lo, _ = delivery_window_utc(start)
    _, hi = delivery_window_utc(end)
    f = forecasts[(forecasts["start_time"] >= lo) & (forecasts["start_time"] < hi)]
    d = f.merge(actuals, on="start_time", how="inner")
    d["horizon_h"] = (d["start_time"] - d["publish_time"]).dt.total_seconds() / 3600
    d = d[(d["horizon_h"] >= 0) & (d["horizon_h"] < HORIZON_EDGES[-1])].copy()
    if d.empty:
        return []
    d["error_mw"] = d["forecast_mw"] - d["actual_mw"]
    d["bucket"] = pd.cut(d["horizon_h"], HORIZON_EDGES, right=False)
    out = []
    for b, g in d.groupby("bucket", observed=True):
        e = g["error_mw"].to_numpy()
        out.append(
            {
                "label": f"{int(b.left)}-{int(b.right)}h",
                "from_h": int(b.left),
                "to_h": int(b.right),
                "n": int(len(g)),
                "mae_mw": float(np.abs(e).mean()),
                "bias_mw": float(e.mean()),
                "p95_abs_error_mw": float(np.quantile(np.abs(e), 0.95)),
            }
        )
    return out
