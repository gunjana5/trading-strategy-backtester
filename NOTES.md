trading strategy backtester

scratch notes for how the pieces connect - nothing official


what this is

paper backtests on yahoo history: a few rules plus optional sklearn model, costs + risk limits, charts and headline metrics in the browser. not live execution.

stack: flask api + react (vite). pandas/sklearn/ta stay in python; charts via recharts


how i laid out the repo

backend/ - all the real logic. app.py is basically a thin router; interesting bits in data/, strategies/, backtester/
frontend/src/ - one screen. App.jsx owns top-level state, components are dumb-ish and just get props
frontend/src/api/client.js - every http call goes through here so i'm not sprinkling fetch + base urls everywhere

no react router on purpose - one page. state is useState in App.jsx (results, loading, error). enough for this


port 5050 (airplay)

moved off 5000 because macos airplay often grabs 5000 and returns 403 to random http. showed up as "tickers: forbidden" in the ui through the vite proxy. flask listens on 5050; vite proxies /api → 127.0.0.1:5050. if you ever see forbidden again check airplay first, not cors


backend pipeline

every backtest run does the same dance:

1. data/fetcher.py - fetch_ohlcv(ticker, start, end)
   wraps yfinance. yahoo sometimes returns multiindex columns or weird casing - i normalise names. strip timezone off the index so json doesn't freak out. auto_adjust=False, fall back to adj close if needed. hits data/cache.py first (sqlite, 24h ttl) so i'm not hammering yahoo on every click

2. strategies/*.py - run(df, ...)
   same contract: dataframe + signal column. 1 = buy, -1 = sell, 0 = hold. keeps the engine reusable

3. backtester/engine.py
   day by day, long-only. on 1 deploy cash at close (worse fill via slippage_bps), pay commission_bps on notional. on -1 flatten. optional stop_loss_pct force-exits an open position; max_drawdown_pct flattens + halts new entries. metrics: total return %, sharpe (ann ret / ann vol from daily equity returns, 252), max dd from rolling peak, win rate from closed round-trips, total_costs = sum of commissions (slippage is in the fill, not that line)

4. data/run_store.py
   every successful POST /api/backtest saves metrics + equity + buy-hold + meta into backtest_runs.db. GET /api/runs lists newest first; GET /api/runs/<id> reloads curves for the history panel

5. app.py
   GET /api/tickers is a hardcoded list of ~20 symbols. POST /api/backtest: fetch once → apply strategy once → backtest TWICE (user costs + zero costs) on the same signals so the ui can overlay "fantasy free fills". ValueError → 400. oos_window = first test_start → last test_end for chart labels


yahoo quirks

yfinance shape drifts - multiindex columns, Adj Close vs Close, empty ranges. fetcher's normalisation is there for that. short date ranges + ml can blow up after indicator warm-up (need enough clean rows). cache key is ticker|start|end; ttl 24h then refetch


the three strategies

moving average - signal only on the cross day (fast above slow = 1, below = -1). stops the sim buying every day we're above the slow line

rsi - ta library. below oversold = 1, above overbought = -1. rule-based not a crossover detector, so you can get chop around the bands. conscious simplicity tradeoff

ml - features: rsi, sma 20/50, macd, volume pct change, 1d/5d returns. label = next day return > 0.5%. default in the ui is walk_forward=true (expanding train window, trade only oos blocks). single 70/30 split still available. train / past bars get signal 0 so we don't pretend we had a model before it existed. model retrains every api call, nothing saved to disk. joblib is in requirements mostly because sklearn expects it


walk-forward (backtester/walk_forward.py)

expanding window: fold k trains on [0 .. test_start), predicts the next block. n_folds 2-8. fold oos accuracies + mean go into validation meta for the honesty banner. if folds disagree wildly, treat the run as unstable. still paper - doesn't invent edge


costs (defaults 5/5 bps)

commission_bps on each buy/sell notional. slippage_bps makes buy fill higher and sell fill lower vs close. buy-hold benchmark uses the same entry cost model so the chart isn't free-vs-paid nonsense. ui can also send max_drawdown_pct / stop_loss_pct (0 = off)


frontend bits worth remembering

StrategySelector - default dates = two years back → today; fetches tickers once with a cancelled flag. client-side checks (fast < slow, oversold < overbought, dates) before hitting the api. costs + walk-forward toggles live here

BacktestResults - snake_case api → camelCase props; honesty / halt banners; "show zero-cost overlay" checkbox. headline metrics stay with-costs; yellow curve is the free-fill fantasy

PerformanceChart - OOS badge + reference line at oos_start when ml validation is present. train bars shaded lightly so interviewers can see we don't trade the train set

RunHistory - GET /api/runs, click row → GET /api/runs/:id, parent swaps results. historyKey bumps after a new run so the list refreshes

sqlite not postgres - on purpose. one person demo. say that if someone asks "why not postgres"

client.js - VITE_API_URL optional; empty = relative /api (vite proxy). wrap network failures with "is flask on 5050?"


stuff that bit me

homebrew python + pep 668 - use backend/.venv, don't pip globally
airplay on 5000 - see above
yfinance column shape - fetcher normalisation
ml needs enough history after warm-up


stuff i'd still come back to

position sizing / shorts (engine is all-in long-only)
fatter cost model (impact, borrow) if i ever pretend this is serious
production: npm run build doesn't get the vite proxy - need VITE_API_URL or one reverse proxy
lazy-load recharts if bundle size ever mattered


quick mental map

fetch_ohlcv (+ cache) → strategy signal → engine (costs/risk) → run_store → json
app.py thin · App.jsx state · client.js fetch · vite proxy → :5050

that's the loop when reopening this repo
