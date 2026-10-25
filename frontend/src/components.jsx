import React from "react";

export function Stat({ label, value, hint, tone }) {
  return (
    <div className={`stat ${tone || ""}`}>
      <div className="k">{label}</div>
      <div className="v">{value}</div>
      {hint && <div className="h">{hint}</div>}
    </div>
  );
}

export function Panel({ title, sub, children }) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      {sub && <p className="sub">{sub}</p>}
      {children}
    </section>
  );
}

export function Loading() {
  return <div className="skeleton" role="status" aria-label="Loading" style={{ minHeight: 260 }} />;
}

export function ErrorBox({ message }) {
  return (
    <div className="error" role="alert">
      <strong>Could not load data.</strong> {message}
    </div>
  );
}

export function useAsync(fn, deps) {
  const [state, setState] = React.useState({ loading: true, data: null, error: null });
  React.useEffect(() => {
    let live = true;
    setState((s) => ({ ...s, loading: true, error: null }));
    fn()
      .then((data) => live && setState({ loading: false, data, error: null }))
      .catch((e) => live && setState({ loading: false, data: null, error: e.message }));
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return state;
}
