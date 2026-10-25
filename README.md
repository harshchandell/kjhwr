# Wind Forecast Monitor

A small web app I built for a UK energy utility's day-ahead buying team. The team has to decide how much power to buy for tomorrow by a fixed time today, and wind is the biggest unknown. The app answers two questions using national-level wind data from Elexon:

1. What is the latest wind forecast the team actually has when they make the decision?
2. How accurate are these forecasts, in numbers, so the error can be planned for?

Scope: purchase decisions made in **January 2026** (decision on day D-1, delivery on day D). Data: Elexon BMRS only, `FUELHH` (actual wind, `fuelType = WIND`) and `WINDFOR` (wind forecasts).

## Links

- **Live app:** https://kjhwr-cyan-iota.vercel.app/
- **Demo video (unlisted, Part 1 client pitch + Part 2 technical review):** https://youtu.be/Mrx3vhGs7Pw

## AI tool disclosure

I used an AI tool (Anthropic's Claude) to help build this project: it helped generate the initial code, tests and documentation. I ran the app and the tests myself and reviewed the code, and I can explain how it works.

## The main idea: the "decision-time forecast"

The `WINDFOR` dataset has many forecasts for the same hour, one for each `publishTime`. A buyer on day D-1 can only use forecasts that were already published at their decision time, and they would use the newest of those. If I took the newest forecast overall, I would be using information from after the decision and the accuracy would look better than it really was.

So for each target hour I do this:

```
forecast = the row with the latest publishTime where publishTime <= cutoff on day D-1
```

The cutoff is **09:00 London time on D-1** by default. This is my assumption, and it can be changed in the app (or with the `DECISION_CUTOFF` environment variable) to match the real deadline.

Note: in the data I downloaded, actuals are half-hourly and forecasts are hourly. They are compared only on the hours where both exist, and the app detects the forecast resolution from the data instead of assuming it.

## Metrics

Error = forecast minus actual. A positive error means the forecast was too high (risk of buying too little).

| Metric | Why it matters |
|---|---|
| MAE and MAE as % of average output | Typical size of a miss |
| RMSE | Punishes large misses |
| Bias | Whether forecasts are systematically too high or too low |
| P95 absolute error | What a bad hour looks like |
| P10 / P90 of signed error | The range where 80% of errors fall. The P90 is used as a "shortfall buffer" |
| Error by day, by hour of day, by lead time | Where and when the forecast is weakest |

## Key findings (January 2026, 09:00 cutoff)

- Mean absolute error was 2,022 MW (17.9% of average output). RMSE was 2,497 MW and the 95th percentile error was 5,268 MW.
- Forecasts ran high: bias was +1,746 MW, and the forecast was above the actual in 85% of hours. I did not investigate the cause.
- Error grows with lead time: 1,654 MW MAE at 0-6 hours ahead versus 2,361 MW at 60-72 hours ahead.
- The worst days were 11, 12 and 28 January (MAE above 4,800 MW).
- For a decision on 15 Jan (delivery 16 Jan), the average forecast wind was 7.9 GW, and the "shortfall buffer" (P90) was 4,154 MW.

## Project structure

```
api/index.py                    Vercel entrypoint (exposes the FastAPI app)
backend/app/config.py           Settings: timezone, cutoff, January 2026 range
backend/app/data.py             Loads the CSV data from data/
backend/app/analysis.py         Analysis functions: decision forecast, metrics, lead time
backend/app/main.py             FastAPI routes (also serves the React build in Docker)
backend/scripts/fetch_data.py   Downloads FUELHH and WINDFOR from Elexon into data/
backend/tests/                  Tests (use small fake data, not the real files)
data/                           wind_actuals.csv, wind_forecasts.csv
frontend/                       React (Vite) app; src/*.jsx are the views, src/api.js makes the API calls
Dockerfile, docker-compose.yml  Container build
vercel.json                     Vercel configuration
docs/VIDEO_SCRIPT.md            Notes I used for the demo video
```

## API

| Endpoint | What it does |
|---|---|
| `GET /api/meta` | Date range, defaults, data coverage |
| `GET /api/decision?decision_date=&cutoff=` | Forecast available at decision time for the next day, plus actuals if available |
| `GET /api/evaluation?start=&end=&cutoff=` | Accuracy metrics: overall, by day, by hour, error histogram |
| `GET /api/horizon?start=&end=` | Error by forecast lead time (uses all published forecasts) |

## How to run it

Use **Python 3.12 or 3.13**. (With Python 3.14, the pinned pandas version crashed for me.) Node.js is needed for the frontend.

### 1. Install and get the data

The data files are already in the repo, so you can skip the download. To refresh them from Elexon:

```bash
python -m venv .venv
source .venv/bin/activate        # on Windows Git Bash: source .venv/Scripts/activate
pip install -r requirements-dev.txt
python backend/scripts/fetch_data.py
```

### 2. Run locally (development)

```bash
# terminal 1: backend
uvicorn backend.app.main:app --reload --port 8000

# terminal 2: frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

### 3. Run tests

```bash
pytest
```

### 4. Run with Docker

```bash
docker compose up --build
```

Open http://localhost:8000. This builds the React app and serves it from the FastAPI backend.
I tested this locally with Docker Desktop on Windows.

## Deployment

The app is deployed on Vercel with the "Other" preset. `vercel.json` builds the React app into static files and bundles `backend/` and `data/` into the Python serverless function at `api/index.py`, which serves the FastAPI backend under `/api`. The CSV files in `data/` are committed because the deployed backend reads them directly.

## Limitations and next steps

- National level and wind only, as the task specified. There is no demand or price data, so the shortfall risk is in MW and not in pounds.
- The data is a snapshot for January 2026. Forecasts with a lead time above 72 hours were dropped to keep the files small.
- The shaded error band on the chart uses all of January, so it is in-sample. A real version would use a rolling window that ends at the decision date.
- The 09:00 cutoff is my assumption.
- Next steps: convert the shortfall risk into cost using price data, add a bias correction, and refresh the data automatically.