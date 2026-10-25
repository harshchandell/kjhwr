def test_meta(client):
    r = client.get("/api/meta")
    assert r.status_code == 200 and r.json()["decision_start"] == "2026-01-01"


def test_decision_has_48_slots_and_respects_cutoff(client):
    r = client.get("/api/decision", params={"decision_date": "2026-01-15", "cutoff": "09:00"})
    assert r.status_code == 200
    body = r.json()
    assert body["delivery_date"] == "2026-01-16" and body["forecast_slots"] == body["expected_slots"]
    assert body["latest_publish_time"] <= body["cutoff_utc"]
    assert all(p["publish_time"] <= body["cutoff_utc"] for p in body["points"])


def test_validation(client):
    assert client.get("/api/decision", params={"decision_date": "2026-03-01"}).status_code == 422
    assert client.get("/api/decision", params={"decision_date": "2026-01-15", "cutoff": "25:99"}).status_code == 422


def test_evaluation_and_horizon(client):
    ev = client.get("/api/evaluation").json()
    assert ev["overall"]["n"] > 1000 and len(ev["daily"]) == 31 and ev["histogram"]
    hz = client.get("/api/horizon").json()["buckets"]
    assert hz and hz[0]["from_h"] == 0
    # synthetic noise grows with lead time, so error must rise from the first to the last bucket
    assert hz[-1]["mae_mw"] > hz[0]["mae_mw"]
