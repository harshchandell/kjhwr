import React from "react";
import { api } from "./api.js";
import { ErrorBox, Loading, useAsync } from "./components.jsx";
import DecisionView from "./DecisionView.jsx";
import EvaluationView from "./EvaluationView.jsx";
import HorizonView from "./HorizonView.jsx";

const TABS = [
  { id: "decision", label: "Tomorrow's wind" },
  { id: "accuracy", label: "Forecast accuracy" },
  { id: "leadtime", label: "Accuracy by lead time" },
];

export default function App() {
  const meta = useAsync(() => api.meta(), []);
  const [tab, setTab] = React.useState("decision");
  const [decisionDate, setDecisionDate] = React.useState(null);
  const [cutoff, setCutoff] = React.useState(null);

  React.useEffect(() => {
    if (meta.data) {
      setDecisionDate((d) => d || meta.data.default_decision_date);
      setCutoff((c) => c || meta.data.default_cutoff);
    }
  }, [meta.data]);

  const m = meta.data;
  const ready = m && decisionDate && cutoff;
  const range = m ? { start: m.decision_start, end: m.decision_end } : null;

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <h1>Wind Forecast Monitor</h1>
            <p>Day-ahead buying: what wind will deliver, and how far to trust the forecast</p>
          </div>
          {ready && (
            <div className="controls">
              <label className="field">
                Decision day (buy for the next day)
                <input type="date" value={decisionDate} min={m.decision_start} max={m.decision_end} onChange={(e) => e.target.value && setDecisionDate(e.target.value)} />
              </label>
              <label className="field">
                Decision cutoff (London time)
                <input type="time" value={cutoff} onChange={(e) => e.target.value && setCutoff(e.target.value)} />
              </label>
            </div>
          )}
        </div>
      </header>

      <nav className="tabs" role="tablist" aria-label="Views">
        {TABS.map((t) => (
          <button key={t.id} role="tab" className="tab" aria-selected={tab === t.id} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </nav>

      <main>
        {meta.loading && <Loading />}
        {meta.error && <ErrorBox message={meta.error} />}
        {ready && tab === "decision" && <DecisionView decisionDate={decisionDate} cutoff={cutoff} />}
        {ready && tab === "accuracy" && <EvaluationView cutoff={cutoff} range={range} />}
        {ready && tab === "leadtime" && <HorizonView range={range} />}
      </main>

      <footer>
        Source: Elexon BMRS (FUELHH actual wind, WINDFOR wind forecast), national level, hourly. Forecast minus actual:
        positive error means the forecast was too high.
      </footer>
    </>
  );
}
