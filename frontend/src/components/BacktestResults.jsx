// costs toggle: with fees vs fantasy zero-cost on the same signals

import { useState } from "react";
import PerformanceChart from "./PerformanceChart.jsx";
import RiskMetrics from "./RiskMetrics.jsx";
import SignalChart from "./SignalChart.jsx";
import "./BacktestResults.css";

export default function BacktestResults({ data }) {
  const [showZeroCost, setShowZeroCost] = useState(false);

  if (!data) return null;
  const {
    equity_curve: equityCurve,
    buy_hold_curve: buyHoldCurve,
    equity_curve_zero_cost: equityZero,
    price_series: priceSeries,
    total_return: totalReturn,
    sharpe_ratio: sharpeRatio,
    max_drawdown: maxDrawdown,
    win_rate: winRate,
    num_trades: numTrades,
    total_costs: totalCosts,
    validation,
    oos_window: oosWindow,
    halted,
    halt_reason: haltReason,
    stop_exits: stopExits,
    commission_bps: commissionBps,
    slippage_bps: slippageBps,
    run_id: runId,
    zero_cost: zeroCost,
  } = data;

  // headline metrics stay "with costs" - zero-cost is the overlay / comparison only
  const metrics = {
    totalReturn,
    sharpeRatio,
    maxDrawdown,
    winRate,
    numTrades,
    totalCosts,
  };

  return (
    <section className="results-root fade-in">
      <div className="results-head">
        <span className="pill">results{runId != null ? ` · run #${runId}` : ""}</span>
        <span className="subtle">
          paper only · costs {commissionBps ?? 0}/{slippageBps ?? 0} bps · signals use past rows only
        </span>
      </div>

      {validation && (
        <div className="honesty-banner" role="note">
          <strong className="oos-tag">OOS only</strong>
          {" - "}
          <strong>{validation.mode === "walk_forward" ? "walk-forward" : "hold-out split"}</strong>
          {" - "}
          {validation.warning}
          {validation.mean_oos_accuracy != null && (
            <span>
              {" "}
              mean oos accuracy: {(validation.mean_oos_accuracy * 100).toFixed(1)}%
            </span>
          )}
          {validation.oos_accuracy != null && validation.mean_oos_accuracy == null && (
            <span> oos accuracy: {(validation.oos_accuracy * 100).toFixed(1)}%</span>
          )}
          {oosWindow?.oos_start && (
            <span>
              {" "}
              · traded from {oosWindow.oos_start}
              {oosWindow.oos_end ? ` → ${oosWindow.oos_end}` : ""}
            </span>
          )}
        </div>
      )}

      {halted && (
        <div className="honesty-banner warn">
          risk halt: {haltReason || "limit hit"}
          {stopExits ? ` · stop-loss exits: ${stopExits}` : ""}
        </div>
      )}

      {validation?.folds?.length > 0 && (
        <div className="fold-table-wrap">
          <table className="fold-table">
            <thead>
              <tr>
                <th>fold</th>
                <th>train end</th>
                <th>test window (OOS)</th>
                <th>oos acc</th>
              </tr>
            </thead>
            <tbody>
              {validation.folds.map((f) => (
                <tr key={f.fold}>
                  <td>{f.fold}</td>
                  <td>{f.train_end}</td>
                  <td>
                    {f.test_start} → {f.test_end}
                  </td>
                  <td>{((f.oos_accuracy ?? 0) * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <label className="cost-toggle">
        <input
          type="checkbox"
          checked={showZeroCost}
          onChange={(e) => setShowZeroCost(e.target.checked)}
        />
        <span>
          show zero-cost overlay
          {zeroCost != null && (
            <em>
              {" "}
              (with costs {totalReturn?.toFixed?.(1)}% vs zero {zeroCost.total_return?.toFixed?.(1)}%)
            </em>
          )}
        </span>
      </label>

      <RiskMetrics
        totalReturn={metrics.totalReturn}
        sharpeRatio={metrics.sharpeRatio}
        maxDrawdown={metrics.maxDrawdown}
        winRate={metrics.winRate}
        numTrades={metrics.numTrades}
        totalCosts={metrics.totalCosts}
      />
      <div className="charts-stack">
        <PerformanceChart
          equityCurve={equityCurve}
          buyHoldCurve={buyHoldCurve}
          zeroCostEquity={equityZero}
          showZeroCost={showZeroCost}
          oosWindow={
            oosWindow ||
            (validation?.folds?.[0]
              ? {
                  oos_start: validation.folds[0].test_start,
                  train_end: validation.folds[0].train_end,
                  oos_end: validation.folds[validation.folds.length - 1].test_end,
                  label: "OOS only",
                }
              : null)
          }
        />
        <SignalChart priceSeries={priceSeries} />
      </div>
    </section>
  );
}
