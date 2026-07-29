// metric tiles - numbers ease in so the board feels less dead

import { useEffect, useState } from "react";
import InfoTip from "./InfoTip.jsx";
import "./RiskMetrics.css";

function useAnimatedScalar(target, durationMs = 1000) {
  const [v, setV] = useState(0);
  useEffect(() => {
    let cancelled = false;
    const start = performance.now();
    const from = 0;
    const animate = (now) => {
      const t = Math.min(1, (now - start) / durationMs);
      // ease-out cubic - snappy at the end
      const eased = 1 - (1 - t) ** 3;
      setV(from + (target - from) * eased);
      if (t < 1 && !cancelled) requestAnimationFrame(animate);
      else if (!cancelled) setV(target);
    };
    requestAnimationFrame(animate);
    return () => {
      cancelled = true;
    };
  }, [target, durationMs]);
  return v;
}

function metricToneTotalReturn(pct) {
  if (pct > 0) return "good";
  if (pct < 0) return "bad";
  return "neutral";
}

function metricToneSharpe(x) {
  if (x >= 1) return "good";
  if (x < 0) return "bad";
  return "neutral";
}

function metricToneDrawdown(pct) {
  if (pct <= 8) return "good";
  if (pct >= 25) return "bad";
  return "neutral";
}

function metricToneWinRate(pct) {
  if (pct >= 50) return "good";
  if (pct < 40) return "bad";
  return "neutral";
}

function metricToneProfitFactor(x) {
  if (x == null) return "neutral";
  if (x >= 1.5) return "good";
  if (x < 1) return "bad";
  return "neutral";
}

export default function RiskMetrics({
  totalReturn,
  sharpeRatio,
  sortinoRatio,
  maxDrawdown,
  winRate,
  avgWinPct,
  avgLossPct,
  timeInMarket,
  profitFactor,
  numTrades,
  totalCosts,
}) {
  const animReturn = useAnimatedScalar(totalReturn ?? 0);
  const animSharpe = useAnimatedScalar(sharpeRatio ?? 0);
  const animSortino = useAnimatedScalar(sortinoRatio ?? 0);
  const animDd = useAnimatedScalar(maxDrawdown ?? 0);
  const animWin = useAnimatedScalar(winRate ?? 0);
  const animAvgWin = useAnimatedScalar(avgWinPct ?? 0);
  const animAvgLoss = useAnimatedScalar(avgLossPct ?? 0);
  const animTim = useAnimatedScalar(timeInMarket ?? 0);
  const animPf = useAnimatedScalar(profitFactor ?? 0);
  const animTrades = useAnimatedScalar(numTrades ?? 0);
  const animCosts = useAnimatedScalar(totalCosts ?? 0);

  const cards = [
    {
      label: "total return",
      tip: "how much the paper account grew or shrank end vs start",
      display: `${animReturn.toFixed(2)}%`,
      tone: metricToneTotalReturn(totalReturn ?? 0),
    },
    {
      label: "sharpe ratio",
      tip: "return vs how bumpy the ride was higher is usually nicer",
      display: animSharpe.toFixed(2),
      tone: metricToneSharpe(sharpeRatio ?? 0),
    },
    {
      label: "sortino",
      tip: "like sharpe but only punishes downside wobbles",
      display: animSortino.toFixed(2),
      tone: metricToneSharpe(sortinoRatio ?? 0),
    },
    {
      label: "max drawdown",
      tip: "worst peak-to-trough drop along the way",
      display: `${animDd.toFixed(2)}%`,
      tone: metricToneDrawdown(maxDrawdown ?? 0),
    },
    {
      label: "win rate",
      tip: "share of closed trades that made money",
      display: `${animWin.toFixed(1)}%`,
      tone: metricToneWinRate(winRate ?? 0),
    },
    {
      label: "avg win",
      tip: "average % gain on the winning trades",
      display: `${animAvgWin.toFixed(2)}%`,
      tone: metricToneTotalReturn(avgWinPct ?? 0),
    },
    {
      label: "avg loss",
      tip: "average % loss on the losing trades",
      display: `${animAvgLoss.toFixed(2)}%`,
      tone: (avgLossPct ?? 0) < 0 ? "bad" : "neutral",
    },
    {
      label: "time in market",
      tip: "percent of days we actually held shares",
      display: `${animTim.toFixed(1)}%`,
      tone: "neutral",
    },
    {
      label: "profit factor",
      tip: "gross wins divided by gross losses above 1 means wins outweighed losses",
      display: profitFactor == null ? "-" : animPf.toFixed(2),
      tone: metricToneProfitFactor(profitFactor),
    },
    {
      label: "trades",
      tip: "how many round trips we closed",
      display: String(Math.max(0, Math.round(animTrades))),
      tone: "neutral",
    },
    {
      label: "total costs",
      tip: "sum of commission fees we charged the sim slippage is in the fills not this line",
      display: `$${animCosts.toFixed(2)}`,
      tone: (totalCosts ?? 0) > 0 ? "bad" : "neutral",
    },
  ];

  return (
    <div className="risk-grid">
      {cards.map((c) => (
        <div key={c.label} className={`risk-card tone-${c.tone}`}>
          <div className="risk-label">
            <span className="label-row">
              {c.label}
              <InfoTip text={c.tip} />
            </span>
          </div>
          <div className="risk-value">{c.display}</div>
        </div>
      ))}
    </div>
  );
}
