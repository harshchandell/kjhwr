"""Synthetic fixtures used ONLY by tests (never shipped as app data)."""
import numpy as np
import pandas as pd
import pytest


@pytest.fixture(scope="session")
def synthetic_dir(tmp_path_factory):
    rng = np.random.default_rng(0)
    d = tmp_path_factory.mktemp("data")
    idx = pd.date_range("2026-01-01", "2026-02-03", freq="30min", tz="UTC", inclusive="left")
    truth = 8000 + 4000 * np.sin(np.arange(len(idx)) / 40) + rng.normal(0, 200, len(idx))
    pd.DataFrame({"startTime": idx.strftime("%Y-%m-%dT%H:%M:%SZ"), "generation": truth.round(0)}).to_csv(
        d / "wind_actuals.csv", index=False
    )
    rows = []
    truth_s = pd.Series(truth, index=idx)
    for pub in pd.date_range("2025-12-29", "2026-02-02", freq="h", tz="UTC"):
        for h in range(0, 73, 1):
            t = pub + pd.Timedelta(hours=h)
            if t in truth_s.index and t.minute == 0:
                for t2 in (t, t + pd.Timedelta(minutes=30)):
                    if t2 in truth_s.index:
                        rows.append((t2, pub, truth_s[t2] + rng.normal(0, 50 + 20 * h)))
    f = pd.DataFrame(rows, columns=["startTime", "publishTime", "generation"])
    for c in ("startTime", "publishTime"):
        f[c] = f[c].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    f.to_csv(d / "wind_forecasts.csv", index=False)
    return d


@pytest.fixture()
def client(synthetic_dir, monkeypatch):
    from fastapi.testclient import TestClient

    from backend.app import data, main

    monkeypatch.setattr(data, "DATA_DIR", synthetic_dir)
    data.load_actuals.cache_clear()
    data.load_forecasts.cache_clear()
    main._evaluation_frame.cache_clear()
    return TestClient(main.app)
