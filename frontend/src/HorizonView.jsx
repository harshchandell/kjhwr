import React from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "./api.js";
import { Panel, Loading, ErrorBox, useAsync } from "./components.jsx";
import { mw, signedMw } from "./format.js";

export default function HorizonView({ range }) {
  const { loading, data, error } = useAsync(() => api.horizon(range.start, range.end), [range.start, range.end]);
  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} />;
  const b = data.buckets;
  if (!b.length) return <div className="empty">No lead-time data available.</div>;

  return (
    <>
      <div className="callout">
        Forecasts are re-issued many times before delivery. This view groups every published forecast by how far ahead it was
        made. A day-ahead decision at 09:00 uses forecasts roughly 15 to 39 hours ahead.
      </div>
      <Panel title="Error by forecast lead time" sub="Lead time is the gap between publication and the hour being forecast. Shorter lead time should mean smaller errors.">
        <div className="chart">
          <ResponsiveContainer>
            <BarChart data={b} margin={{ top: 8, right: 8, left: 4, bottom: 0 }}>
              <CartesianGrid stroke="#e6edf0" vertical={false} />
              <XAxis dataKey="label" stroke="#5b7280" fontSize={12} />
              <YAxis stroke="#5b7280" fontSize={12} tickFormatter={(v) => `${v / 1000}`} label={{ value: "GW", angle: -90, position: "insideLeft", fill: "#5b7280" }} />
              <Tooltip formatter={(v) => mw(v)} />
              <Legend />
              <Bar dataKey="mae_mw" name="Mean absolute error" fill="#0b7a75" isAnimationActive={false} />
              <Bar dataKey="p95_abs_error_mw" name="95th percentile error" fill="#0e2a35" isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Panel>
      <Panel title="Lead-time detail">
        <div className="table-wrap">
          <table>
            <thead><tr><th>Lead time</th><th>Forecasts</th><th>MAE</th><th>Bias</th><th>P95 error</th></tr></thead>
            <tbody>
              {b.map((r) => (
                <tr key={r.label}>
                  <td>{r.label}</td>
                  <td>{r.n.toLocaleString("en-GB")}</td>
                  <td>{mw(r.mae_mw)}</td>
                  <td className={r.bias_mw > 0 ? "pos" : "neg"}>{signedMw(r.bias_mw)}</td>
                  <td>{mw(r.p95_abs_error_mw)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </>
  );
}
