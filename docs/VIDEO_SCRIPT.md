# Video script (max 10 minutes: Part 1 ~4:30, Part 2 ~5:00)

Record the screen with the deployed app open. Speak slowly; rehearse once. Upload to YouTube as **Unlisted** and open the link in incognito before submitting.

## Part 1 - Client pitch (0:00-4:30)

**0:00 Problem (30s).** "Your team buys power in the GB day-ahead market by mid-morning on the day before delivery. Wind is the biggest weather-driven unknown. You need two answers: what will wind deliver tomorrow, and how far can I trust that number?"

**0:30 Tomorrow's wind tab (90s).** Pick 15 Jan. Point to the big average GW number, peak/lowest/total energy. "This is the latest forecast published before your 09:00 decision, not the latest ever published. That matters: using later forecasts would make accuracy look better than what you actually experienced." Show the chart and the shaded band. Point to Shortfall risk: "In 1 of 10 half-hours in January, wind came in at least this far below forecast. That is the extra thermal volume to consider covering."

**2:00 Forecast accuracy tab (90s).** Read MAE, bias, P95. "On average the forecast is off by X MW, Y% of output. Bias tells you whether it runs high or low. P95 tells you what a bad half-hour looks like." Show daily chart: "Some days are far harder than others." Show hour-of-day chart.

**3:30 Lead time tab (45s).** "Forecasts improve as delivery approaches. At your decision time you're working with 15-39 hour-ahead forecasts. This view shows what that costs you in accuracy compared with later updates."

**4:15 Close (15s).** "Change the cutoff time to match your desk's real deadline and every number updates. Next steps: add demand and price data so the shortfall risk converts straight into pounds."

## Part 2 - Technical review (4:30-9:45)

**4:30 Overview (60s).** Show the README tree. "React + Vite frontend, FastAPI backend, pandas for analysis. Data is a snapshot of two Elexon datasets for January 2026, fetched by one script, so serverless hosting is fast and reproducible."

**5:30 Core logic (120s).** Open `backend/app/analysis.py`. Walk `decision_forecast`: filter delivery day, filter `publish_time <= cutoff`, sort, keep last per `start_time`. "This is the one decision that makes the evaluation honest. Test `test_decision_forecast_picks_latest_before_cutoff_and_ignores_later` locks it in." Mention London timezone handling and the DST test. Show `metrics`: error = forecast - actual, so positive = over-forecast = under-buying risk. Explain MAE, RMSE, bias, P95, P10/P90 buffer.

**7:30 API and data layer (60s).** Open `main.py`: four endpoints, input validation (date range, HH:MM regex), NaN-safe JSON, 503 with a clear message if data is missing. Open `data.py` and `fetch_data.py`: chunked requests, retries, lead-time filter.

**8:30 Frontend (45s).** `api.js` is the only place with HTTP. Three view components, shared `useAsync` hook with cancellation. Recharts for charts.

**9:15 Practices and deployment (30s).** Run `pytest` on screen (green). Show the Dockerfile (multi-stage) and `vercel.json`. Say AI tools were used and disclosed in the README. Mention limitations: national level only, wind only, no demand or price data, cutoff is an assumption.
