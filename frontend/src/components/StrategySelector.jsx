// sends json to /api/backtest

import { useEffect, useMemo, useState } from "react";
import { fetchTickers } from "../api/client.js";
import "./StrategySelector.css";

function formatDate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export default function StrategySelector({ onRun, loading, error }) {
  const [tickers, setTickers] = useState([]);
  const [ticker, setTicker] = useState("aapl");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [strategy, setStrategy] = useState("moving_average_crossover");
  const [fast, setFast] = useState(20);
  const [slow, setSlow] = useState(50);
  const [rsiPeriod, setRsiPeriod] = useState(14);
  const [overbought, setOverbought] = useState(70);
  const [oversold, setOversold] = useState(30);
  const [walkForward, setWalkForward] = useState(true);
  const [nFolds, setNFolds] = useState(3);
  const [commissionBps, setCommissionBps] = useState(5);
  const [slippageBps, setSlippageBps] = useState(5);
  const [maxDrawdownPct, setMaxDrawdownPct] = useState(0);
  const [stopLossPct, setStopLossPct] = useState(0);
  const [loadErr, setLoadErr] = useState(null);
  const [formErr, setFormErr] = useState(null);

  useEffect(() => {
    const today = new Date();
    const twoYearsAgo = new Date();
    twoYearsAgo.setFullYear(today.getFullYear() - 2);
    setEnd(formatDate(today));
    setStart(formatDate(twoYearsAgo));
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchTickers()
      .then((data) => {
        if (!cancelled && data.tickers?.length) {
          setTickers(data.tickers);
          setTicker(data.tickers[0]);
        }
      })
      .catch((e) => {
        if (!cancelled) setLoadErr(e.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const params = useMemo(() => {
    const base = {
      commission_bps: commissionBps,
      slippage_bps: slippageBps,
      max_drawdown_pct: maxDrawdownPct || null,
      stop_loss_pct: stopLossPct || null,
    };
    if (strategy === "moving_average_crossover") {
      return { ...base, fast, slow };
    }
    if (strategy === "rsi_strategy") {
      return { ...base, period: rsiPeriod, overbought, oversold };
    }
    return { ...base, walk_forward: walkForward, n_folds: nFolds };
  }, [
    strategy,
    fast,
    slow,
    rsiPeriod,
    overbought,
    oversold,
    walkForward,
    nFolds,
    commissionBps,
    slippageBps,
    maxDrawdownPct,
    stopLossPct,
  ]);

  const handleSubmit = (e) => {
    e.preventDefault();
    setFormErr(null);
    if (strategy === "moving_average_crossover" && fast >= slow) {
      setFormErr("fast period must be smaller than slow period");
      return;
    }
    if (strategy === "rsi_strategy" && oversold >= overbought) {
      setFormErr("oversold must be below overbought");
      return;
    }
    if (new Date(start) > new Date(end)) {
      setFormErr("start date must be on or before end date");
      return;
    }
    onRun({
      ticker,
      start,
      end,
      strategy,
      params,
      commission_bps: commissionBps,
      slippage_bps: slippageBps,
      max_drawdown_pct: maxDrawdownPct || null,
      stop_loss_pct: stopLossPct || null,
    });
  };

  const showMa = strategy === "moving_average_crossover";
  const showRsi = strategy === "rsi_strategy";
  const showMl = strategy === "ml_signal";

  return (
    <form className="strategy-panel" onSubmit={handleSubmit}>
      <div className="panel-heading">controls</div>

      {loadErr && <div className="inline-msg warn">tickers: {loadErr}</div>}

      <label className="field">
        <span>ticker</span>
        <select value={ticker} onChange={(e) => setTicker(e.target.value)} disabled={!tickers.length}>
          {tickers.map((t) => (
            <option key={t} value={t}>
              {t.toUpperCase()}
            </option>
          ))}
        </select>
      </label>

      <div className="field-row">
        <label className="field">
          <span>start</span>
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} required />
        </label>
        <label className="field">
          <span>end</span>
          <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} required />
        </label>
      </div>

      <label className="field">
        <span>strategy</span>
        <select value={strategy} onChange={(e) => setStrategy(e.target.value)}>
          <option value="moving_average_crossover">moving average crossover</option>
          <option value="rsi_strategy">rsi strategy</option>
          <option value="ml_signal">ml signal</option>
        </select>
      </label>

      {showMa && (
        <div className="slider-block">
          <label className="slider-label">
            <span>fast period ({fast})</span>
            <input
              type="range"
              min={5}
              max={50}
              value={fast}
              onChange={(e) => setFast(Number(e.target.value))}
            />
          </label>
          <label className="slider-label">
            <span>slow period ({slow})</span>
            <input
              type="range"
              min={10}
              max={200}
              value={slow}
              onChange={(e) => setSlow(Number(e.target.value))}
            />
          </label>
        </div>
      )}

      {showRsi && (
        <div className="slider-block">
          <label className="slider-label">
            <span>rsi period ({rsiPeriod})</span>
            <input
              type="range"
              min={2}
              max={30}
              value={rsiPeriod}
              onChange={(e) => setRsiPeriod(Number(e.target.value))}
            />
          </label>
          <label className="slider-label">
            <span>overbought ({overbought})</span>
            <input
              type="range"
              min={55}
              max={95}
              value={overbought}
              onChange={(e) => setOverbought(Number(e.target.value))}
            />
          </label>
          <label className="slider-label">
            <span>oversold ({oversold})</span>
            <input
              type="range"
              min={5}
              max={45}
              value={oversold}
              onChange={(e) => setOversold(Number(e.target.value))}
            />
          </label>
        </div>
      )}

      {showMl && (
        <div className="slider-block">
          <label className="check-label">
            <input
              type="checkbox"
              checked={walkForward}
              onChange={(e) => setWalkForward(e.target.checked)}
            />
            <span>walk-forward validation</span>
          </label>
          {walkForward && (
            <label className="slider-label">
              <span>folds ({nFolds})</span>
              <input
                type="range"
                min={2}
                max={6}
                value={nFolds}
                onChange={(e) => setNFolds(Number(e.target.value))}
              />
            </label>
          )}
          <p className="hint">
            ml only trades out-of-sample bars. walk-forward expands the train window each fold to
            reduce optimistic overfitting.
          </p>
        </div>
      )}

      <div className="panel-heading subtle">costs &amp; risk</div>
      <div className="slider-block">
        <label className="slider-label">
          <span>commission ({commissionBps} bps)</span>
          <input
            type="range"
            min={0}
            max={50}
            value={commissionBps}
            onChange={(e) => setCommissionBps(Number(e.target.value))}
          />
        </label>
        <label className="slider-label">
          <span>slippage ({slippageBps} bps)</span>
          <input
            type="range"
            min={0}
            max={50}
            value={slippageBps}
            onChange={(e) => setSlippageBps(Number(e.target.value))}
          />
        </label>
        <label className="slider-label">
          <span>max drawdown halt ({maxDrawdownPct || "off"}%)</span>
          <input
            type="range"
            min={0}
            max={50}
            value={maxDrawdownPct}
            onChange={(e) => setMaxDrawdownPct(Number(e.target.value))}
          />
        </label>
        <label className="slider-label">
          <span>stop loss ({stopLossPct || "off"}%)</span>
          <input
            type="range"
            min={0}
            max={40}
            value={stopLossPct}
            onChange={(e) => setStopLossPct(Number(e.target.value))}
          />
        </label>
      </div>

      <button type="submit" className="run-btn" disabled={loading || !tickers.length}>
        {loading ? (
          <span className="btn-inner">
            <span className="spinner" aria-hidden />
            running…
          </span>
        ) : (
          "run backtest"
        )}
      </button>

      {(formErr || error) && (
        <div className="inline-msg error" role="alert">
          {formErr || error}
        </div>
      )}
    </form>
  );
}
