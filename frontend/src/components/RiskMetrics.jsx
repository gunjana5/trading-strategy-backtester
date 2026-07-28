import { useEffect, useState } from "react";
import "./RiskMetrics.css";

function useAnimatedScalar(target, durationMs = 1000) {
  const [v, setV] = useState(0);
  useEffect(() => {
    let cancelled = false;
    const start = performance.now();
    const from = 0;
    const animate = (now) => {
      const t = Math.min(1, (now - start) / durationMs);
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

export default function RiskMetrics({
  totalReturn,
  sharpeRatio,
  maxDrawdown,
  winRate,
  numTrades,
  totalCosts,
}) {
  const animReturn = useAnimatedScalar(totalReturn ?? 0);
  const animSharpe = useAnimatedScalar(sharpeRatio ?? 0);
  const animDd = useAnimatedScalar(maxDrawdown ?? 0);
  const animWin = useAnimatedScalar(winRate ?? 0);
  const animTrades = useAnimatedScalar(numTrades ?? 0);
  const animCosts = useAnimatedScalar(totalCosts ?? 0);

  const cards = [
    {
      label: "total return",
      display: `${animReturn.toFixed(2)}%`,
      tone: metricToneTotalReturn(totalReturn ?? 0),
    },
    {
      label: "sharpe ratio",
      display: animSharpe.toFixed(2),
      tone: metricToneSharpe(sharpeRatio ?? 0),
    },
    {
      label: "max drawdown",
      display: `${animDd.toFixed(2)}%`,
      tone: metricToneDrawdown(maxDrawdown ?? 0),
    },
    {
      label: "win rate",
      display: `${animWin.toFixed(1)}%`,
      tone: metricToneWinRate(winRate ?? 0),
    },
    {
      label: "trades",
      display: String(Math.max(0, Math.round(animTrades))),
      tone: "neutral",
    },
    {
      label: "total costs",
      display: `$${animCosts.toFixed(2)}`,
      tone: (totalCosts ?? 0) > 0 ? "bad" : "neutral",
    },
  ];

  return (
    <div className="risk-grid">
      {cards.map((c) => (
        <div key={c.label} className={`risk-card tone-${c.tone}`}>
          <div className="risk-label">{c.label}</div>
          <div className="risk-value">{c.display}</div>
        </div>
      ))}
    </div>
  );
}
