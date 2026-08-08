// empty BASE = relative /api and vite proxy; set VITE_API_URL if hitting flask directly
const BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

function apiUrl(path) {
  const p = path.startsWith("/") ? path : `/${path}`;
  return BASE ? `${BASE}${p}` : p;
}

export async function parseJson(res) {
  // read as text first so a non-json 500 still gives a useful error
  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    throw new Error("invalid json from server");
  }
  if (!res.ok) {
    const msg = data.error || res.statusText || "request failed";
    throw new Error(msg);
  }
  return data;
}

export function wrapNetworkError(err) {
  // browsers throw TypeError when fetch can't connect at all
  if (err instanceof TypeError || err?.name === "TypeError") {
    const hint =
      "cannot reach the api. start the backend first: cd backend && source .venv/bin/activate && python app.py (listening on port 5050).";
    throw new Error(hint);
  }
  const msg = err?.message || String(err);
  if (/load failed|failed to fetch|networkerror/i.test(msg)) {
    throw new Error(
      "cannot reach the api - is the flask server running on port 5050? (see readme backend section)"
    );
  }
  throw err;
}

export async function fetchTickers() {
  try {
    const res = await fetch(apiUrl("/api/tickers"));
    return await parseJson(res);
  } catch (e) {
    wrapNetworkError(e);
  }
}

export async function runBacktest(config) {
  // POST body = full strategy + cost payload from StrategySelector
  try {
    const res = await fetch(apiUrl("/api/backtest"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    return await parseJson(res);
  } catch (e) {
    wrapNetworkError(e);
  }
}

export async function fetchRuns({ limit = 20, ticker, strategy } = {}) {
  try {
    const qs = new URLSearchParams();
    qs.set("limit", String(limit));
    if (ticker) qs.set("ticker", ticker);
    if (strategy) qs.set("strategy", strategy);
    const res = await fetch(apiUrl(`/api/runs?${qs}`));
    return await parseJson(res);
  } catch (e) {
    wrapNetworkError(e);
  }
}

export async function fetchRun(runId) {
  try {
    const res = await fetch(apiUrl(`/api/runs/${runId}`));
    return await parseJson(res);
  } catch (e) {
    wrapNetworkError(e);
  }
}

export async function deleteRun(runId) {
  try {
    const res = await fetch(apiUrl(`/api/runs/${runId}`), { method: "DELETE" });
    return await parseJson(res);
  } catch (e) {
    wrapNetworkError(e);
  }
}

export async function clearRuns() {
  try {
    const res = await fetch(apiUrl("/api/runs"), { method: "DELETE" });
    return await parseJson(res);
  } catch (e) {
    wrapNetworkError(e);
  }
}

export async function runCompare(config) {
  try {
    const res = await fetch(apiUrl("/api/compare"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    return await parseJson(res);
  } catch (e) {
    wrapNetworkError(e);
  }
}

export async function runMaSensitivity(config) {
  try {
    const res = await fetch(apiUrl("/api/ma-sensitivity"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    return await parseJson(res);
  } catch (e) {
    wrapNetworkError(e);
  }
}

export async function saveRunNote(runId, note) {
  try {
    const res = await fetch(apiUrl(`/api/runs/${runId}/note`), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ note }),
    });
    return await parseJson(res);
  } catch (e) {
    wrapNetworkError(e);
  }
}
