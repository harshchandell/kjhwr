# Wind Forecast Monitor

A web app for a UK energy utility's day-ahead buying team. It answers two questions using national-level Elexon wind data:

1. **What is the latest wind forecast available when the day-ahead decision has to be made?**
2. **How accurate are these forecasts, quantitatively?** (so the error can be priced into the purchase)

Scope: purchase decisions made in **January 2026** (decision on day D-1 for delivery on day D). Data: Elexon BMRS only, `FUELHH` (actual wind, `fuelType = WIND`) and `WINDFOR` (wind forecasts).

**Live app:** `<ADD YOUR VERCEL / HEROKU URL HERE>`
**Demo video:** `<ADD YOUR UNLISTED YOUTUBE URL HERE>`

## AI tool disclosure

This project was built with the assistance of an AI tool (Anthropic's Claude), which generated the initial code, tests and documentation. I reviewed, ran and take responsibility for all of it.

## Key design decision: the "decision-time forecast"

`WINDFOR` contains many forecasts for each half-hour (one per `publishTime`). A buyer on day D-1 can only use forecasts published **before their decision cutoff**, and should use the **latest of those**. Using the latest forecast overall would leak information from after the decision and overstate accuracy. So for every target half-hour:

```
forecast = row with max(publishTime) where publishTime <= cutoff(D-1)
```

The cutoff defaults to **09:00 London time on D-1** (configurable in the UI and via `DECISION_CUTOFF`). This is an assumption: set it to your desk's real deadline relative to day-ahead gate closure.

## Metrics (error = forecast − actual; positive = forecast too high)

| Metric | Why it matters to a buyer |
|---|---|
| MAE, MAE % of mean actual | Typical miss size, comparable across days |
| RMSE | Penalises large misses |
| Bias | Systematic over/under-forecasting |
| P90 / P95 absolute error | What a bad half-hour looks like |
| P10 / P90 signed error | The 80% error band; P90 is a shortfall buffer: actual wind is below forecast by more than this in 1 of 10 half-hours |
| Error by hour of day, by day, by lead time | Where and when the forecast is weakest |

## Repository layout

```
api/index.py              Vercel serverless entrypoint (exposes the FastAPI app)
backend/app/config.py     Settings: timezone, cutoff, January 2026 scope
backend/app/data.py       Loads the CSV snapshots from data/
backend/app/analysis.py   Pure analysis functions (decision forecast, metrics, lead time)
backend/app/main.py       FastAPI routes + static serving of the React build
backend/scripts/fetch_data.py   Downloads FUELHH/WINDFOR from Elexon into data/
backend/tests/            pytest suite (synthetic fixtures, used only by tests)
data/                     wind_actuals.csv, wind_forecasts.csv (created by fetch_data.py)
frontend/                 React (Vite) app; views in src/*.jsx, HTTP in src/api.js
Dockerfile, docker-compose.yml   Multi-stage container build
vercel.json               Vercel config (static frontend + Python function)
docs/VIDEO_SCRIPT.md      Talking points for the demo video
```

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/meta` | Date range, defaults, data coverage |
| `GET /api/decision?decision_date=&cutoff=` | Decision-time forecast for the next day, with actuals if available |
| `GET /api/evaluation?start=&end=&cutoff=` | Accuracy metrics overall, daily, hourly, error histogram |
| `GET /api/horizon?start=&end=` | Error vs forecast lead time (all forecasts) |

## Run it

### 1. Get the data (once; needs internet)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python backend/scripts/fetch_data.py        # writes data/*.csv — commit these files
```

### 2. Docker (recommended)

```bash
docker compose up --build        # http://localhost:8000
```

### 3. Local development

```bash
uvicorn backend.app.main:app --reload --port 8000     # terminal 1
cd frontend && npm install && npm run dev             # terminal 2 -> http://localhost:5173
pytest                                                # run tests
```

## Deploy

**Vercel:** import the repo, leave the root directory as is. `vercel.json` builds the React app to static files and bundles `backend/` and `data/` into the Python function at `api/index.py`. Make sure `data/*.csv` is committed.
**Heroku (alternative):** `heroku stack:set container && git push heroku main` uses the Dockerfile as is.

## Limitations and next steps

- National level, wind only, as specified. No demand or price data, so shortfall risk is in MW, not £.
- Data is a snapshot; refresh with `fetch_data.py`. Forecasts with lead time over 72 h are dropped to keep the file small.
- The error band on the chart uses all of January (in-sample); a production version would use a rolling window ending at the decision date.
- Next: convert shortfall risk to cost using day-ahead and imbalance prices, and add alerts for high-risk days.
