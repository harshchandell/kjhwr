from datetime import date, time

import pandas as pd

from backend.app import analysis


def _fc(rows):
    df = pd.DataFrame(rows, columns=["start_time", "publish_time", "forecast_mw"])
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
    df["publish_time"] = pd.to_datetime(df["publish_time"], utc=True)
    return df


def test_cutoff_uses_london_time_in_winter_and_summer():
    assert analysis.cutoff_utc(date(2026, 1, 14), time(9, 0)) == pd.Timestamp("2026-01-14 09:00", tz="UTC")
    assert analysis.cutoff_utc(date(2026, 7, 14), time(9, 0)) == pd.Timestamp("2026-07-14 08:00", tz="UTC")


def test_decision_forecast_picks_latest_before_cutoff_and_ignores_later():
    f = _fc(
        [
            ("2026-01-15 12:00", "2026-01-13 12:00", 100),  # older
            ("2026-01-15 12:00", "2026-01-14 08:00", 200),  # latest before 09:00 cutoff -> chosen
            ("2026-01-15 12:00", "2026-01-14 09:00", 300),  # exactly at cutoff -> allowed
            ("2026-01-15 12:00", "2026-01-14 09:30", 999),  # after cutoff -> must be ignored (leakage)
        ]
    )
    out = analysis.decision_forecast(f, date(2026, 1, 14), time(9, 0))
    assert len(out) == 1 and out.forecast_mw.iloc[0] == 300


def test_decision_forecast_excludes_other_delivery_days():
    f = _fc([("2026-01-14 12:00", "2026-01-13 12:00", 1), ("2026-01-16 12:00", "2026-01-13 12:00", 2)])
    assert analysis.decision_forecast(f, date(2026, 1, 14), time(9, 0)).empty


def test_metrics_known_values():
    df = pd.DataFrame({"forecast_mw": [110.0, 90.0, 130.0], "actual_mw": [100.0, 100.0, 100.0]})
    df["error_mw"] = df.forecast_mw - df.actual_mw
    m = analysis.metrics(df)
    assert m["mae_mw"] == (10 + 10 + 30) / 3
    assert round(m["bias_mw"], 6) == round((10 - 10 + 30) / 3, 6)
    assert m["over_forecast_share_pct"] == (2 / 3) * 100
    assert analysis.metrics(df.iloc[0:0]) == {"n": 0}
