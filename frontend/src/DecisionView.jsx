import React from "react";
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "./api.js";
import { Stat, Panel, Loading, ErrorBox, useAsync } from "./components.jsx";
import { dateTimeLabel, gw, longDate, mw, signedMw, timeLabel } from "./format.js";

function ChartTip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div style={{ background: "#fff", border: "1px solid #d6e0e4", borderRadius: 8, padding: "8px 10px", fontSize: 13 }}>
      <strong>{timeLabel(p.t)}</strong>
      <div style={{ color: "#0b7a75" }}>Forecast: {mw(p.forecast)}</div>
      {p.actual != null && <div>Actual: {mw(p.actual)}</div>}
      {p.band && <div style={{ color: "#5b7280" }}>Likely range: {mw(p.band[0])} to {mw(p.band[1])}</div>}
      <div style={{ color: "#5b7280" }}>Published {dateTimeLabel(p.publish)}</div>
    </div>
  );
}

export default function DecisionView({ decisionDate, cutoff }) {
  const { loading, data, error } = useAsync(() => api.decision(decisionDate, cutoff), [decisionDate, cutoff]);
  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} />;

  const pts = data.points.map((p) => ({
    t: new Date(p.t).getTime(),
    forecast: p.forecast_mw,
    actual: p.actual_mw,
    publish: p.publish_time,
    band: p.band_low_mw != null ? [Math.max(0, p.band_low_mw), p.band_high_mw] : null,
  }));
  const s = data.summary;
  const risk = data.typical_error_mw.p90;
  const dm = data.day_metrics;
  const incomplete = data.forecast_slots < data.expected_slots;

  return (
    <>
      <div className="hero">
        <div className="hero-main">
          <p className="lead">Expected wind generation on {longDate(data.delivery_date)}</p>
          <div className="big">
            {(s.mean_mw / 1000).toFixed(1)}
            <small>GW average</small>
          </div>
          <p className="note">
            Latest forecast available at your {data.cutoff_local} decision on {longDate(data.decision_date)}. It was
            published {dateTimeLabel(data.latest_publish_time)}.
          </p>
        </div>
        <div className="stats">
          <Stat label="Peak" value={gw(s.max_mw)} hint="Highest hour" />
          <Stat label="Lowest" value={gw(s.min_mw)} hint="Lowest hour" />
          <Stat label="Total energy" value={`${(s.energy_mwh / 1000).toFixed(1)} GWh`} hint="Whole delivery day" />
          <Stat
            tone="warn"
            label="Shortfall risk"
            value={risk != null ? `up to ${Math.round(risk).toLocaleString("en-GB")} MW` : "-"}
            hint="Actual wind falls this far below forecast in 1 of 10 hours (January)"
          />
        </div>
      </div>

      {incomplete && (
        <div className="callout warn">
          Only {data.forecast_slots} of {data.expected_slots} hours have a forecast published before the cutoff.
        </div>
      )}

      <Panel
        title="Forecast for the delivery day"
        sub="Hourly national wind forecast, in London time. The shaded band is the range that actual output fell in for 80% of hours in January 2026."
      >
        <div className="chart">
          <ResponsiveContainer>
            <ComposedChart data={pts} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
              <CartesianGrid stroke="#e6edf0" vertical={false} />
              <XAxis dataKey="t" type="number" scale="time" domain={["dataMin", "dataMax"]} tickFormatter={timeLabel} tickCount={9} stroke="#5b7280" />
              <YAxis tickFormatter={(v) => `${(v / 1000).toFixed(0)}`} stroke="#5b7280" label={{ value: "GW", angle: -90, position: "insideLeft", fill: "#5b7280" }} />
              <Tooltip content={<ChartTip />} />
              <Area dataKey="band" stroke="none" fill="#0b7a75" fillOpacity={0.14} isAnimationActive={false} />
              <Line dataKey="forecast" stroke="#0b7a75" strokeWidth={2.5} dot={false} isAnimationActive={false} />
              {data.has_actuals && <Line dataKey="actual" stroke="#0e2a35" strokeWidth={2} dot={false} connectNulls={false} isAnimationActive={false} />}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        <div className="legend">
          <span><i style={{ background: "#0b7a75" }} />Forecast at decision time</span>
          {data.has_actuals && <span><i style={{ background: "#0e2a35" }} />Actual generation</span>}
          <span><i className="band" />Usual error range (80%)</span>
        </div>
      </Panel>

      {data.has_actuals && dm.n > 0 && (
        <Panel title="How this forecast performed" sub="Compared with what was actually generated on the delivery day.">
          <div className="stats" style={{ gridTemplateColumns: "repeat(4, minmax(0, 1fr))" }}>
            <Stat label="Mean absolute error" value={mw(dm.mae_mw)} hint={dm.mae_pct_of_mean_actual != null ? `${dm.mae_pct_of_mean_actual.toFixed(1)}% of average output` : ""} />
            <Stat label="Bias" value={signedMw(dm.bias_mw)} hint={dm.bias_mw > 0 ? "Forecast was too high" : "Forecast was too low"} />
            <Stat label="95th percentile error" value={mw(dm.p95_abs_error_mw)} hint="Worst 1 in 20 hours" />
            <Stat label="Largest miss" value={mw(dm.max_abs_error_mw)} />
          </div>
        </Panel>
      )}
    </>
  );
}
