// empty BASE = relative /api and vite proxy; set VITE_API_URL if hitting flask directly
const BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

function apiUrl(path) {
  const p = path.startsWith("/") ? path : `/${path}`;
  return BASE ? `${BASE}${p}` : p;
}

async function parseJson(res) {
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

function wrapNetworkError(err) {
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
