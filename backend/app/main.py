"""FastAPI application: thin HTTP layer over analysis.py."""
from __future__ import annotations

import math
from datetime import date, timedelta
from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import analysis
from .config import DECISION_END, DECISION_START, DEFAULT_CUTOFF, DEFAULT_DECISION_DATE, FRONTEND_DIST, parse_hhmm
from .data import DataNotFound, load_actuals, load_forecasts

app = FastAPI(title="Wind Forecast Monitor API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])

CUTOFF_RE = r"^([01]\d|2[0-3]):[0-5]\d$"


#  helpers
def _clean(o):
    """Recursively make values JSON-safe (NaN/inf -> None, rounded floats)."""
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_clean(v) for v in o]
    if isinstance(o, float):
        return None if (math.isnan(o) or math.isinf(o)) else round(o, 2)
    return o


def _iso(ts) -> str | None:
    return None if pd.isna(ts) else pd.Timestamp(ts).tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


def _check_decision_date(d: date) -> None:
    if not (DECISION_START <= d <= DECISION_END):
        raise HTTPException(422, f"Decision date must be between {DECISION_START} and {DECISION_END}.")


@app.exception_handler(DataNotFound)
async def _data_missing(_, exc: DataNotFound):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@lru_cache(maxsize=16)
def _evaluation_frame(cutoff: str) -> pd.DataFrame:
    return analysis.build_evaluation_frame(
        load_forecasts(), load_actuals(), DECISION_START, DECISION_END, parse_hhmm(cutoff)
    )


#  endpoints
@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/meta")
def meta():
    a, f = load_actuals(), load_forecasts()
    return _clean(
        {
            "decision_start": DECISION_START.isoformat(),
            "decision_end": DECISION_END.isoformat(),
            "default_decision_date": DEFAULT_DECISION_DATE.isoformat(),
            "default_cutoff": DEFAULT_CUTOFF,
            "timezone": "Europe/London",
            "actuals": {"rows": len(a), "from": _iso(a.start_time.min()), "to": _iso(a.start_time.max())},
            "forecasts": {
                "rows": len(f),
                "first_publish": _iso(f.publish_time.min()),
                "last_publish": _iso(f.publish_time.max()),
            },
        }
    )


@app.get("/api/decision")
def decision(
    decision_date: date = Query(..., description="Day D-1 on which the purchase decision is made"),
    cutoff: str = Query(DEFAULT_CUTOFF, pattern=CUTOFF_RE, description="London-local HH:MM decision cutoff"),
):
    """The forecast the buyer would have had in hand, plus actuals if delivery has happened."""
    _check_decision_date(decision_date)
    ct = parse_hhmm(cutoff)
    fc = analysis.decision_forecast(load_forecasts(), decision_date, ct)
    if fc.empty:
        raise HTTPException(404, "No forecast was published before the cutoff for this delivery day.")
    df = fc.merge(load_actuals(), on="start_time", how="left")
    df["error_mw"] = df["forecast_mw"] - df["actual_mw"]

    band = analysis.metrics(_evaluation_frame(cutoff))
    p10, p90 = band.get("error_p10_mw"), band.get("error_p90_mw")
    points = []
    for r in df.itertuples():
        points.append(
            {
                "t": _iso(r.start_time),
                "forecast_mw": r.forecast_mw,
                "actual_mw": r.actual_mw,
                "publish_time": _iso(r.publish_time),
                # actual = forecast - error, so an 80% range of errors gives an 80% range for actuals
                "band_low_mw": r.forecast_mw - p90 if p90 is not None else None,
                "band_high_mw": r.forecast_mw - p10 if p10 is not None else None,
            }
        )
    delivery = decision_date + timedelta(days=1)
    # WINDFOR resolution is detected rather than assumed: 48 slots/day if half-hourly, else 24 (hourly).
    expected = 48 if (load_forecasts()["start_time"].dt.minute == 30).any() else 24
    return _clean(
        {
            "decision_date": decision_date.isoformat(),
            "delivery_date": delivery.isoformat(),
            "cutoff_local": cutoff,
            "cutoff_utc": _iso(analysis.cutoff_utc(decision_date, ct)),
            "expected_slots": expected,
            "forecast_slots": len(df),
            "latest_publish_time": _iso(df["publish_time"].max()),
            "summary": {
                "mean_mw": float(df.forecast_mw.mean()),
                "min_mw": float(df.forecast_mw.min()),
                "max_mw": float(df.forecast_mw.max()),
                "energy_mwh": float(df.forecast_mw.sum() * (24 / expected)),
            },
            "has_actuals": bool(df.actual_mw.notna().any()),
            "day_metrics": analysis.metrics(df),
            "typical_error_mw": {"p10": p10, "p90": p90},
            "points": points,
        }
    )


@app.get("/api/evaluation")
def evaluation(
    start: date = Query(DECISION_START),
    end: date = Query(DECISION_END),
    cutoff: str = Query(DEFAULT_CUTOFF, pattern=CUTOFF_RE),
):
    """Accuracy of decision-time forecasts across a range of decision days."""
    _check_decision_date(start)
    _check_decision_date(end)
    if end < start:
        raise HTTPException(422, "End date must not be before start date.")
    df = _evaluation_frame(cutoff)
    df = df[(df.decision_date >= start) & (df.decision_date <= end)]
    if df.empty:
        raise HTTPException(404, "No data for this range.")
    return _clean(
        {
            "cutoff_local": cutoff,
            "overall": analysis.metrics(df),
            "daily": analysis.daily_metrics(df),
            "hourly": analysis.hourly_metrics(df),
            "histogram": analysis.error_histogram(df),
        }
    )


@app.get("/api/horizon")
def horizon(start: date = Query(DECISION_START), end: date = Query(DECISION_END)):
    """Error vs forecast lead time, using every published forecast (not just the decision-time one)."""
    _check_decision_date(start)
    _check_decision_date(end)
    return _clean({"buckets": analysis.horizon_metrics(load_forecasts(), load_actuals(), start, end)})


#  serve the React build (Docker)
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        candidate = FRONTEND_DIST / path
        if path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
