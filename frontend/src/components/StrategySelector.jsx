// sends json to /api/backtest

import { useEffect, useMemo, useState } from "react";
import { fetchTickers } from "../api/client.js";
import InfoTip from "./InfoTip.jsx";
import "./StrategySelector.css";

function formatDate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function TipLabel({ children, tip }) {
  return (
    <span className="label-row">
      {children}
      <InfoTip text={tip} />
    </span>
  );
}

export default function StrategySelector({ onRun, onCompare, loading, error }) {
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
  const [positionSizePct, setPositionSizePct] = useState(100);
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
      cancelled = true; // ignore late responses after unmount
    };
  }, []);

  const params = useMemo(() => {
    const base = {
      commission_bps: commissionBps,
      slippage_bps: slippageBps,
      max_drawdown_pct: maxDrawdownPct || null,
      stop_loss_pct: stopLossPct || null,
      position_size_pct: positionSizePct,
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
    positionSizePct,
  ]);

  const buildPayload = () => ({
    ticker,
    start,
    end,
    strategy,
    params,
    commission_bps: commissionBps,
    slippage_bps: slippageBps,
    max_drawdown_pct: maxDrawdownPct || null,
    stop_loss_pct: stopLossPct || null,
    position_size_pct: positionSizePct,
  });

  const validate = () => {
    setFormErr(null);
    if (strategy === "moving_average_crossover" && fast >= slow) {
      setFormErr("fast period must be smaller than slow period");
      return false;
    }
    if (strategy === "rsi_strategy" && oversold >= overbought) {
      setFormErr("oversold must be below overbought");
      return false;
    }
    if (new Date(start) > new Date(end)) {
      setFormErr("start date must be on or before end date");
      return false;
    }
    return true;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!validate()) return;
    onRun(buildPayload());
  };

  const handleCompare = (e) => {
    e.preventDefault();
    if (!validate()) return;
    onCompare?.(buildPayload());
  };

  const showMa = strategy === "moving_average_crossover";
  const showRsi = strategy === "rsi_strategy";
  const showMl = strategy === "ml_signal";

  return (
    <form className="strategy-panel" onSubmit={handleSubmit}>
      <div className="panel-heading">
        <TipLabel tip="this whole left bit is how you set up a paper run">controls</TipLabel>
      </div>

      {loadErr && <div className="inline-msg warn">tickers: {loadErr}</div>}

      <label className="field">
        <TipLabel tip="which stock or etf to pretend-trade using yahoo history">ticker</TipLabel>
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
          <TipLabel tip="first day of price history we pull">start</TipLabel>
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} required />
        </label>
        <label className="field">
          <TipLabel tip="last day of price history we pull">end</TipLabel>
          <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} required />
        </label>
      </div>

      <label className="field">
        <TipLabel tip="the rules that decide buy sell or do nothing each day">strategy</TipLabel>
        <select value={strategy} onChange={(e) => setStrategy(e.target.value)}>
          <option value="moving_average_crossover">moving average crossover</option>
          <option value="rsi_strategy">rsi strategy</option>
          <option value="ml_signal">ml signal</option>
        </select>
      </label>

      {showMa && (
        <div className="slider-block">
          <label className="slider-label">
            <TipLabel tip="short moving average window in days reacts quicker">
              fast period ({fast})
            </TipLabel>
            <input
              type="range"
              min={5}
              max={50}
              value={fast}
              onChange={(e) => setFast(Number(e.target.value))}
            />
          </label>
          <label className="slider-label">
            <TipLabel tip="long moving average window smoother trend line">
              slow period ({slow})
            </TipLabel>
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
            <TipLabel tip="how many days rsi looks back for overbought/oversold">
              rsi period ({rsiPeriod})
            </TipLabel>
            <input
              type="range"
              min={2}
              max={30}
              value={rsiPeriod}
              onChange={(e) => setRsiPeriod(Number(e.target.value))}
            />
          </label>
          <label className="slider-label">
            <TipLabel tip="rsi above this = maybe sell vibe">overbought ({overbought})</TipLabel>
            <input
              type="range"
              min={55}
              max={95}
              value={overbought}
              onChange={(e) => setOverbought(Number(e.target.value))}
            />
          </label>
          <label className="slider-label">
            <TipLabel tip="rsi below this = maybe buy vibe">oversold ({oversold})</TipLabel>
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
            <TipLabel tip="trains then tests on later chunks so we dont cheat with future data">
              walk-forward validation
            </TipLabel>
          </label>
          {walkForward && (
            <label className="slider-label">
              <TipLabel tip="how many train/test chunks to chop the timeline into">
                folds ({nFolds})
              </TipLabel>
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

      <div className="panel-heading subtle">
        <TipLabel tip="fees and safety switches so the sim is less fantasy">costs &amp; risk</TipLabel>
      </div>
      <div className="slider-block">
        <label className="slider-label">
          <TipLabel tip="fake broker fee in basis points 100 bps = 1 percent">
            commission ({commissionBps} bps)
          </TipLabel>
          <input
            type="range"
            min={0}
            max={50}
            value={commissionBps}
            onChange={(e) => setCommissionBps(Number(e.target.value))}
          />
        </label>
        <label className="slider-label">
          <TipLabel tip="we worsen the fill a bit so buys cost more sells get less">
            slippage ({slippageBps} bps)
          </TipLabel>
          <input
            type="range"
            min={0}
            max={50}
            value={slippageBps}
            onChange={(e) => setSlippageBps(Number(e.target.value))}
          />
        </label>
        <label className="slider-label">
          <TipLabel tip="if portfolio drops this % from its peak we flatten and stop buying">
            max drawdown halt ({maxDrawdownPct || "off"}%)
          </TipLabel>
          <input
            type="range"
            min={0}
            max={50}
            value={maxDrawdownPct}
            onChange={(e) => setMaxDrawdownPct(Number(e.target.value))}
          />
        </label>
        <label className="slider-label">
          <TipLabel tip="auto sell if an open trade is down this % from entry">
            stop loss ({stopLossPct || "off"}%)
          </TipLabel>
          <input
            type="range"
            min={0}
            max={40}
            value={stopLossPct}
            onChange={(e) => setStopLossPct(Number(e.target.value))}
          />
        </label>
        <label className="slider-label">
          <TipLabel tip="how much cash to put into each buy 100 means go all in">
            position size ({positionSizePct}% of cash)
          </TipLabel>
          <input
            type="range"
            min={10}
            max={100}
            step={5}
            value={positionSizePct}
            onChange={(e) => setPositionSizePct(Number(e.target.value))}
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
          <span className="btn-inner">
            run backtest
            <InfoTip text="fires the whole paper sim and shows charts metrics and trades on the right" />
          </span>
        )}
      </button>

      <button
        type="button"
        className="compare-btn"
        disabled={loading || !tickers.length || !onCompare}
        onClick={handleCompare}
      >
        <span className="btn-inner">
          compare ma / rsi / ml
          <InfoTip text="same ticker dates costs - runs all three and shows a side by side table" />
        </span>
      </button>

      {(formErr || error) && (
        <div className="inline-msg error" role="alert">
          {formErr || error}
        </div>
      )}
    </form>
  );
}
