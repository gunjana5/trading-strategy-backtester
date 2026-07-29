// sidebar controls + main results panel

import { useCallback, useState } from "react";
import { runBacktest, runCompare } from "./api/client.js";
import BacktestResults from "./components/BacktestResults.jsx";
import CompareTable from "./components/CompareTable.jsx";
import DeskStamp from "./components/DeskStamp.jsx";
import RunHistory from "./components/RunHistory.jsx";
import SiteHelp from "./components/SiteHelp.jsx";
import StrategySelector from "./components/StrategySelector.jsx";
import TickerTape from "./components/TickerTape.jsx";
import "./App.css";

export default function App() {
  const [results, setResults] = useState(null);
  const [compare, setCompare] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [historyKey, setHistoryKey] = useState(0);

  const handleRun = useCallback(async (config) => {
    setLoading(true);
    setError(null);
    setCompare(null);
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

  const handleCompare = useCallback(async (config) => {
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const data = await runCompare(config);
      setCompare(data);
    } catch (e) {
      setCompare(null);
      setError(e?.message || "compare failed");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSelectRun = useCallback((row) => {
    setCompare(null);
    setResults(row);
  }, []);

  return (
    <div className="app-shell">
      <SiteHelp />
      <aside className="sidebar">
        <header className="brand">
          <div className="brand-mark" aria-hidden>
            <img src="/icons/candles.svg" alt="" />
          </div>
          <div className="brand-lockup">
            <span className="brand-kicker">paper desk</span>
            <span className="brand-text">trading strategy</span>
            <span className="brand-text">backtester</span>
          </div>
        </header>
        <div className="stamp-row" aria-hidden>
          <span className="stamp stamp-paper">paper only</span>
          <span className="stamp stamp-desk">not live money</span>
        </div>
        <div className="spark-strip" aria-hidden>
          <img src="/icons/spark.svg" alt="" />
        </div>
        <p className="tagline">
          yahoo history · costs + risk · compare strategies · click any ? if a word looks weird
        </p>
        <StrategySelector
          onRun={handleRun}
          onCompare={handleCompare}
          loading={loading}
          error={error}
        />
        <RunHistory onSelect={handleSelectRun} refreshKey={historyKey} />
      </aside>
      <div className="desk-col">
        <TickerTape />
        <main className="main">
          <div className="main-top">
            <div className="main-top-copy">
              <span className="main-eyebrow">gunjana · paper desk</span>
              <p className="main-lede">
                run one strategy for charts, or compare all three under the same fees
              </p>
            </div>
            <DeskStamp />
          </div>
          <div className="main-inner">
            {!results && !compare && !loading && (
              <div className="empty-state">
                <div className="empty-card">
                  <div className="empty-title">run a backtest</div>
                  <p className="empty-body">
                    pick a ticker and dates on the left, tweak costs / risk, hit run - or compare ma
                    / rsi / ml under the same costs. poke the ? icons if a word looks weird
                  </p>
                  <div className="empty-icons" aria-hidden>
                    <img src="/icons/candles.svg" alt="" />
                    <img src="/icons/spark.svg" alt="" />
                    <img src="/icons/ticket.svg" alt="" />
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
            <CompareTable data={compare} />
            <BacktestResults data={results} />
          </div>
        </main>
      </div>
    </div>
  );
}
