const TZ = "Europe/London";

export const gw = (mw, d = 1) => (mw == null ? "-" : `${(mw / 1000).toFixed(d)} GW`);
export const mw = (v, d = 0) => (v == null ? "-" : `${Number(v).toLocaleString("en-GB", { maximumFractionDigits: d })} MW`);
export const signedMw = (v) => (v == null ? "-" : `${v > 0 ? "+" : ""}${Math.round(v).toLocaleString("en-GB")} MW`);
export const pct = (v, d = 1) => (v == null ? "-" : `${v.toFixed(d)}%`);

export const timeLabel = (ms) =>
  new Date(ms).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: TZ });

export const dateTimeLabel = (iso) =>
  iso
    ? new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: TZ })
    : "-";

export const longDate = (isoDate) =>
  new Date(`${isoDate}T12:00:00Z`).toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" });

export const shortDate = (isoDate) =>
  new Date(`${isoDate}T12:00:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
