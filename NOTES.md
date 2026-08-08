trading strategy backtester

scratch notes for how the pieces connect - nothing official


what this is

paper backtests on yahoo history: a few rules plus optional sklearn model, costs + risk limits, charts and headline metrics in the browser. not live execution.

stack: flask api + react (vite). pandas/sklearn/ta stay in python; charts via recharts (lazy-loaded)


how i laid out the repo

backend/ - all the real logic. app.py is basically a thin router; interesting bits in data/, strategies/, backtester/
frontend/src/ - one screen. App.jsx owns top-level state, components are dumb-ish and just get props
frontend/src/api/client.js - every http call goes through here so i'm not sprinkling fetch + base urls everywhere

no react router on purpose - one page. state is useState in App.jsx (results, loading, error). enough for this


port 5050 (airplay)

moved off 5000 because macos airplay often grabs 5000 and returns 403 to random http. showed up as "tickers: forbidden" in the ui through the vite proxy. flask listens on 5050; vite proxies /api -> 127.0.0.1:5050. if you ever see forbidden again check airplay first, not cors


backend pipeline

every backtest run does the same dance:

1. data/fetcher.py - fetch_ohlcv(ticker, start, end)
   wraps yfinance. yahoo sometimes returns multiindex columns or weird casing - i normalise names. strip timezone off the index so json doesn't freak out. auto_adjust=False, fall back to adj close if needed. hits data/cache.py first (sqlite, 24h ttl) so i'm not hammering yahoo on every click. ticker validated in app.py (preset list + custom, reject junk)

2. strategies/*.py - run(df, ...)
   same contract: dataframe + signal column. 1 = buy, -1 = sell, 0 = hold. keeps the engine reusable

3. backtester/engine.py
   day by day. default fill_timing=next_bar (signal on bar i fills at close of i+1; last signal may never fill). same_bar still available. long-only by default; allow_short opens a short on -1 when flat (no borrow cost). on 1 deploy position_size_pct of cash (worse fill via slippage_bps), pay commission_bps on notional. optional stop_loss_pct / max_drawdown_pct. metrics: total return %, sharpe + sortino, max dd, win rate, avg win/loss %, time-in-market, profit factor, total_costs. closed trades go into a blotter list. oos_metrics_block rebases from first oos date for ml honesty

4. data/run_store.py
   every successful POST /api/backtest saves metrics + equity + buy-hold + meta into backtest_runs.db. GET /api/runs lists newest first; GET /api/runs/<id> reloads curves; DELETE /api/runs/<id> or DELETE /api/runs clears. docker volume keeps the db across restarts

5. app.py
   GET /api/tickers is a hardcoded list of ~20 symbols; custom tickers still accepted on backtest with validation. POST /api/backtest: fetch once -> apply strategy once -> backtest TWICE (user costs + zero costs) on the same signals so the ui can overlay "fantasy free fills". dropped buy_hold_curve_zero_cost (unused). ValueError -> 400; unexpected errors -> generic 500 (no stack leak). walk_forward defaults True when omitted (matches ui). oos_window + oos_metrics on ml runs. POST /api/ma-sensitivity wraps moving_average.sensitivity_grid


yahoo quirks

yfinance shape drifts - multiindex columns, Adj Close vs Close, empty ranges. fetcher's normalisation is there for that. short date ranges + ml can blow up after indicator warm-up (need enough clean rows). cache key is ticker|start|end; ttl 24h then refetch


the three strategies

moving average - signal only on the cross day (fast above slow = 1, below = -1). stops the sim buying every day we're above the slow line

rsi - ta library. below oversold = 1, above overbought = -1. rule-based not a crossover detector, so you can get chop around the bands. conscious simplicity tradeoff

ml - strategies/ml_strategy.py is just a thin facade so app.py has one import. the real work (features, labels, train/predict, expanding folds) is in backtester/walk_forward.py. features: rsi, sma 20/50, macd, volume pct change, 1d/5d returns. label = next day return > 0.5%. default walk_forward=true in facade + api + ui. train / past bars get signal 0. model retrains every api call. headline sharpe/return still include flat in-sample equity - use oos_metrics for the honest slice


walk-forward (backtester/walk_forward.py)

expanding window: fold k trains on [0 .. test_start), predicts the next block. n_folds 2-8. fold oos accuracies + mean go into validation meta. still paper - doesn't invent edge


ma sensitivity - POST /api/ma-sensitivity + small ui table. signal counts only (not sharpe). pairs default [(5,20),(10,30),(20,50),(50,200)]


costs (defaults 5/5 bps)

commission_bps on each buy/sell notional. slippage_bps makes buy fill higher and sell fill lower vs close. buy-hold benchmark uses the same entry cost model. ui can also send max_drawdown_pct / stop_loss_pct (0 = off), position_size_pct, fill_timing, allow_short


frontend bits worth remembering

StrategySelector - default dates = two years back -> today; preset select + custom ticker; fill timing + allow short; costs + walk-forward; ma sensitivity button

BacktestResults - snake_case api -> camelCase props; honesty / halt banners; oos_metrics block; zero-cost overlay; TradeBlotter; desk note; csv export; charts lazy-loaded

CompareTable - POST /api/compare - ma/rsi/ml under same costs

PerformanceChart - OOS badge + reference line at oos_start when ml validation is present

RunHistory - GET /api/runs, click row, delete one, clear all

sqlite not postgres - on purpose. one person demo.

client.js - VITE_API_URL optional; wrap network failures with "is flask on 5050?". vitest covers wrapNetworkError


stuff that bit me

homebrew python + pep 668 - use backend/.venv, don't pip globally
airplay on 5000 - see above
yfinance column shape - fetcher normalisation
ml needs enough history after warm-up
venv path broke after folder move - recreate .venv if py.test shebang points at an old path


stuff i'd still come back to

multi-ticker portfolio (engine is single-name; shorts are the cheap extension)
fatter cost model (impact, borrow) if i ever pretend this is serious
production: npm run build doesn't get the vite proxy - need VITE_API_URL or one reverse proxy
# done: next-bar fills, oos_metrics, custom ticker, ma grid ui, delete runs, vitest smoke, allow_short
# done: position sizing %, trade blotter, sortino / exposure-ish metrics, ./run.sh


quick mental map

fetch_ohlcv (+ cache) -> strategy signal -> engine (fills/costs/risk/sizing) -> run_store -> json
app.py thin · App.jsx state · client.js fetch · vite proxy -> :5050

that's the loop when reopening this repo
