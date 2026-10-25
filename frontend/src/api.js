// All HTTP access lives here. VITE_API_BASE is empty in production (same origin).
const BASE = import.meta.env.VITE_API_BASE || "";

async function get(path, params = {}) {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`${BASE}${path}${qs ? `?${qs}` : ""}`);
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) detail = body.detail.map((d) => d.msg).join("; ");
    } catch {
      /* keep default */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  meta: () => get("/api/meta"),
  decision: (decision_date, cutoff) => get("/api/decision", { decision_date, cutoff }),
  evaluation: (start, end, cutoff) => get("/api/evaluation", { start, end, cutoff }),
  horizon: (start, end) => get("/api/horizon", { start, end }),
};
