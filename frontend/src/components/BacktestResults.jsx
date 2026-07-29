// costs toggle: with fees vs fantasy zero-cost on the same signals

import { useState } from "react";
import InfoTip from "./InfoTip.jsx";
import PerformanceChart from "./PerformanceChart.jsx";
import RiskMetrics from "./RiskMetrics.jsx";
import SignalChart from "./SignalChart.jsx";
import TradeBlotter from "./TradeBlotter.jsx";
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
    sortino_ratio: sortinoRatio,
    max_drawdown: maxDrawdown,
    win_rate: winRate,
    avg_win_pct: avgWinPct,
    avg_loss_pct: avgLossPct,
    time_in_market: timeInMarket,
    profit_factor: profitFactor,
    num_trades: numTrades,
    total_costs: totalCosts,
    trades,
    validation,
    oos_window: oosWindow,
    halted,
    halt_reason: haltReason,
    stop_exits: stopExits,
    commission_bps: commissionBps,
    slippage_bps: slippageBps,
    position_size_pct: positionSizePct,
    run_id: runId,
    zero_cost: zeroCost,
  } = data;

  return (
    <section className="results-root fade-in">
      <div className="results-head">
        <span className="pill">
          <span className="label-row">
            results{runId != null ? ` · run #${runId}` : ""}
            <InfoTip text="output of the last paper run you kicked off or reopened" />
          </span>
        </span>
        <span className="subtle">
          paper only · costs {commissionBps ?? 0}/{slippageBps ?? 0} bps · size{" "}
          {positionSizePct ?? 100}% · signals use past rows only
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
        <span className="label-row">
          show zero-cost overlay
          <InfoTip text="draws a fantasy curve with fees set to zero so you can see if costs ate the edge" />
          {zeroCost != null && (
            <em>
              {" "}
              (with costs {totalReturn?.toFixed?.(1)}% vs zero {zeroCost.total_return?.toFixed?.(1)}%)
            </em>
          )}
        </span>
      </label>

      <RiskMetrics
        totalReturn={totalReturn}
        sharpeRatio={sharpeRatio}
        sortinoRatio={sortinoRatio}
        maxDrawdown={maxDrawdown}
        winRate={winRate}
        avgWinPct={avgWinPct}
        avgLossPct={avgLossPct}
        timeInMarket={timeInMarket}
        profitFactor={profitFactor}
        numTrades={numTrades}
        totalCosts={totalCosts}
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
      <TradeBlotter trades={trades} />
    </section>
  );
}
