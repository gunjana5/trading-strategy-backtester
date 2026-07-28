// sidebar controls + main results panel

import { useCallback, useState } from "react";
import { runBacktest } from "./api/client.js";
import BacktestResults from "./components/BacktestResults.jsx";
import RunHistory from "./components/RunHistory.jsx";
import StrategySelector from "./components/StrategySelector.jsx";
import "./App.css";

export default function App() {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [historyKey, setHistoryKey] = useState(0);

  const handleRun = useCallback(async (config) => {
    setLoading(true);
    setError(null);
    try {
      const data = await runBacktest(config);
      setResults(data);
      setHistoryKey((k) => k + 1);
    } catch (e) {
      setResults(null);
      setError(e?.message || "backtest failed");
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <header className="brand">
          <div className="brand-lockup">
            <span className="brand-text">trading strategy</span>
            <span className="brand-text">backtester</span>
          </div>
          <span className="brand-cursor" aria-hidden />
        </header>
        <p className="tagline">
          paper runs · yahoo history · costs, risk limits, walk-forward honesty
        </p>
        <StrategySelector onRun={handleRun} loading={loading} error={error} />
        <RunHistory onSelect={setResults} refreshKey={historyKey} />
      </aside>
      <main className="main">
        <div className="main-inner">
          {!results && !loading && (
            <div className="empty-state">
              <div className="empty-card">
                <div className="empty-title">run a backtest</div>
                <p className="empty-body">
                  choose ticker and dates, set costs / risk, pick a strategy, press run. ml uses
                  hold-out or walk-forward so in-sample bars are not traded.
                </p>
                <div className="empty-dots">
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            </div>
          )}
          {loading && (
            <div className="loading-banner">
              <span className="loading-pulse" />
              running the pipeline…
            </div>
          )}
          <BacktestResults data={results} />
        </div>
      </main>
    </div>
  );
}
