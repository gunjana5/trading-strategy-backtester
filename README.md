# trading strategy backtester

## what it is

Paper backtests in the browser: Yahoo history -> MA / RSI / ML signals -> long-only-by-default sim with transaction costs, risk limits, next-bar fills, and walk-forward honesty on the ML path. Not live trading advice.

## layout

```
trading-strategy-backtester/
  README.md
  NOTES.md                    # scratch for future me
  run.sh                      # flask + vite together
  docker-compose.yml          # api + ui containers
  .github/workflows/ci.yml    # pytest + frontend build
  backend/                    # flask api + strategies + engine
  backend/app.py              # thin http router
  backend/backtester/         # engine + walk-forward
  backend/strategies/         # ma / rsi / ml facade (signals only)
  backend/data/               # yahoo fetcher, cache, run_store
  backend/tests/              # pytest (mocked yahoo)
  backend/Dockerfile
  frontend/                   # react vite ui
  frontend/src/               # desk components + api client
  frontend/Dockerfile
```

## quick start

```bash
./run.sh
```

Starts Flask on :5050 and the Vite UI on :5173 (opens the browser).

Or with Docker (api needs network for Yahoo):

```bash
docker compose up --build
```

UI on http://localhost:5173, API on http://localhost:5050 (browser calls the API via `VITE_API_URL`).

Or manually:

```bash
# backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py          # http://127.0.0.1:5050

# frontend (new terminal)
cd frontend
npm install
npm run dev            # http://localhost:5173 - proxies /api -> :5050
```

## stack

Python · Flask · pandas · scikit-learn · ta · SQLite · React · Vite · Recharts · pytest · Vitest

## how its wired

```mermaid
flowchart LR
  UI["React + Vite UI"]
  API["Flask API :5050"]
  Fetch["fetcher + SQLite cache"]
  Strat["strategies\nMA / RSI / ML"]
  Eng["backtester engine\ncosts · stop-loss · DD halt"]
  Store["run history SQLite"]

  UI -->|"POST /api/backtest"| API
  API --> Fetch
  Fetch --> Strat
  Strat --> Eng
  Eng --> Store
  API -->|"JSON curves + metrics"| UI
  UI -->|"GET /api/runs"| Store
```

UI posts ticker / dates / strategy / costs -> Flask fetches (or hits the 24h cache) -> strategy stamps a `signal` column -> engine walks day by day -> metrics + curves go back as JSON and land in the run history db. Vite proxies `/api` to `:5050` in dev so the browser stays same-origin.

## whats interesting

- costs are first-class - commission + slippage in bps, not a free fantasy fill
- **next-bar fills by default** - signal on day t fills at day t+1 close (same-bar still available as a toggle)
- **with costs vs zero-cost toggle** - same signals, two equity curves, so "edge" that dies on fees is obvious
- risk limits: optional stop-loss and max-drawdown halt (flatten, no new buys)
- position size % of cash (not forced all-in)
- optional **shorting** (off by default) - `-1` can open a short when flat; no borrow cost modelled
- trade blotter - closed round-trips with entry/exit, pnl %, reason, fees
- metrics beyond a green curve: Sortino, avg win/loss, time-in-market, profit factor
- **compare mode** - same ticker/dates/costs, MA vs RSI vs ML in one table
- **desk note** on a run - short judgment line you save after looking at the charts
- **csv export** - metrics + trades download
- ML path: **OOS only** badge + train/test date labels on the chart; **oos_metrics** block rebases headline numbers from the first OOS bar; walk-forward is the API default (`ml_strategy` is a thin wrapper - train/predict lives in `walk_forward`)
- MA sensitivity grid in the UI (signal counts via `POST /api/ma-sensitivity`)
- custom ticker input alongside the preset list
- run history in SQLite - click a past run, delete one, or clear all
- strategies stay dumb: they only emit `1 / -1 / 0`; the engine owns fills and risk

## limitations

- paper only - no brokerage, no live orders, no "this will make money"
- **fills**: default is next-bar close (more honest). same-bar mode still exists - signal and fill share that day's close, which real systems usually avoid
- simple cost model - constant bps, not venue fees or impact; shorts have no borrow / locate cost
- long-only is the default story; optional shorts are a thin paper extension on one ticker - no multi-name portfolio
- ML is a toy classifier (label ~= next day up > 0.5%); walk-forward helps, doesn't erase overfitting. `strategies/ml_strategy.py` is only the app-facing facade
- **ML headline Sharpe / return still include flat in-sample equity** while trading signals are OOS-only - the equity chart shows the full window with OOS labels; use the **oos_metrics** block for numbers from the first OOS bar onward
- Yahoo data - free delayed/adjusted history; gaps and adjustments happen
- **SQLite on purpose** for run history - single-user demo. Postgres would only matter if many people hit this at once; not worth the ops overhead here.

## tests

```bash
cd backend && pytest -q
cd frontend && npm test && npm run build
```

## demo

```bash
./run.sh
```

Or the manual quick start above (API on :5050, UI on :5173).
