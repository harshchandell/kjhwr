import React from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis, ComposedChart } from "recharts";
import { api } from "./api.js";
import { Stat, Panel, Loading, ErrorBox, useAsync } from "./components.jsx";
import { mw, pct, shortDate, signedMw } from "./format.js";

const axis = { stroke: "#5b7280", fontSize: 12 };

export default function EvaluationView({ cutoff, range }) {
  const { loading, data, error } = useAsync(() => api.evaluation(range.start, range.end, cutoff), [cutoff, range.start, range.end]);
  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} />;
  const o = data.overall;
  if (!o.n) return <div className="empty">No actual generation is available yet for this period.</div>;

  const daily = data.daily.filter((d) => d.n > 0).map((d) => ({ ...d, label: shortDate(d.delivery_date) }));
  const hist = data.histogram.map((h) => ({ ...h, label: `${Math.round(h.mid_mw)}` }));

  return (
    <>
      <div className="callout">
        Every forecast here is the latest one published before {data.cutoff_local} on the day before delivery, so the
        accuracy shown is what a buyer would really have experienced. {o.n.toLocaleString("en-GB")} hours across
        January 2026 decisions.
      </div>

      <div className="stats" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", marginBottom: 20 }}>
        <Stat label="Mean absolute error" value={mw(o.mae_mw)} hint={`${pct(o.mae_pct_of_mean_actual)} of average output`} />
        <Stat label="RMSE" value={mw(o.rmse_mw)} hint="Penalises large misses" />
        <Stat label="Bias" value={signedMw(o.bias_mw)} hint={o.bias_mw > 0 ? "Forecasts run high on average" : "Forecasts run low on average"} />
        <Stat label="95th percentile error" value={mw(o.p95_abs_error_mw)} hint="Worst 1 in 20 hours" />
        <Stat tone="warn" label="Shortfall buffer (P90)" value={mw(o.error_p90_mw)} hint="Actual below forecast by more than this in 1 of 10 hours" />
        <Stat label="Over-forecast share" value={pct(o.over_forecast_share_pct, 0)} hint="Hours where forecast was above actual" />
      </div>

      <Panel title="Error by delivery day" sub="Mean absolute error of the decision-time forecast for each day. Tall bars are days where extra caution would have paid off.">
        <div className="chart short">
          <ResponsiveContainer>
            <BarChart data={daily} margin={{ top: 8, right: 8, left: 4, bottom: 0 }}>
              <CartesianGrid stroke="#e6edf0" vertical={false} />
              <XAxis dataKey="label" {...axis} interval={2} />
              <YAxis {...axis} tickFormatter={(v) => `${v / 1000}`} label={{ value: "GW", angle: -90, position: "insideLeft", fill: "#5b7280" }} />
              <Tooltip formatter={(v) => mw(v)} labelFormatter={(l) => `Delivery ${l}`} />
              <ReferenceLine y={o.mae_mw} stroke="#b45309" strokeDasharray="4 4" />
              <Bar dataKey="mae_mw" name="MAE" fill="#0b7a75" isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Panel>

      <div className="grid2">
        <Panel title="How errors are distributed" sub="Forecast minus actual. Right of zero means the forecast was too high, which risks buying too little.">
          <div className="chart short">
            <ResponsiveContainer>
              <BarChart data={hist} margin={{ top: 8, right: 8, left: 4, bottom: 0 }}>
                <CartesianGrid stroke="#e6edf0" vertical={false} />
                <XAxis dataKey="label" {...axis} interval={3} label={{ value: "Error (MW)", position: "insideBottom", offset: -2, fill: "#5b7280" }} height={40} />
                <YAxis {...axis} />
                <Tooltip formatter={(v) => [v, "Hours"]} labelFormatter={(l) => `Around ${l} MW`} />
                <Bar dataKey="count" fill="#0e2a35" isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="Error by time of day" sub="Average error for each hour of the delivery day (London time).">
          <div className="chart short">
            <ResponsiveContainer>
              <ComposedChart data={data.hourly} margin={{ top: 8, right: 8, left: 4, bottom: 0 }}>
                <CartesianGrid stroke="#e6edf0" vertical={false} />
                <XAxis dataKey="hour" {...axis} tickFormatter={(h) => `${String(h).padStart(2, "0")}:00`} interval={3} />
                <YAxis {...axis} />
                <Tooltip formatter={(v) => mw(v)} labelFormatter={(h) => `${String(h).padStart(2, "0")}:00`} />
                <ReferenceLine y={0} stroke="#5b7280" />
                <Line dataKey="mae_mw" name="Mean absolute error" stroke="#0b7a75" strokeWidth={2.5} dot={false} isAnimationActive={false} />
                <Line dataKey="bias_mw" name="Bias" stroke="#b45309" strokeWidth={2} dot={false} isAnimationActive={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <div className="legend">
            <span><i style={{ background: "#0b7a75" }} />Mean absolute error</span>
            <span><i style={{ background: "#b45309" }} />Bias</span>
          </div>
        </Panel>
      </div>

      <Panel title="Day-by-day results">
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Delivery day</th><th>MAE</th><th>RMSE</th><th>Bias</th><th>P95 error</th><th>Avg actual</th></tr>
            </thead>
            <tbody>
              {daily.map((d) => (
                <tr key={d.decision_date}>
                  <td>{shortDate(d.delivery_date)}</td>
                  <td>{mw(d.mae_mw)}</td>
                  <td>{mw(d.rmse_mw)}</td>
                  <td className={d.bias_mw > 0 ? "pos" : "neg"}>{signedMw(d.bias_mw)}</td>
                  <td>{mw(d.p95_abs_error_mw)}</td>
                  <td>{mw(d.mean_actual_mw)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </>
  );
}
