// sqlite history from /api/runs - click to reload charts

import { useCallback, useEffect, useState } from "react";
import { fetchRun, fetchRuns } from "../api/client.js";
import InfoTip from "./InfoTip.jsx";
import "./RunHistory.css";

export default function RunHistory({ onSelect, refreshKey }) {
  const [runs, setRuns] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchRuns({ limit: 12 });
      setRuns(data.runs || []);
    } catch (e) {
      setError(e?.message || "could not load runs");
      setRuns([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  const openRun = async (id) => {
    try {
      const row = await fetchRun(id);
      if (!row.equity_curve) {
        setError("this older run has no stored equity curve - re-run to refresh history");
        return;
      }
      // reshape sqlite row into the same shape as a fresh /api/backtest response
      onSelect?.({
        run_id: row.id,
        equity_curve: row.equity_curve,
        buy_hold_curve: row.buy_hold_curve || [],
        price_series: [], // not stored - signal chart stays empty on reopen
        total_return: row.total_return,
        sharpe_ratio: row.sharpe_ratio,
        sortino_ratio: row.meta?.metrics_extra?.sortino_ratio,
        max_drawdown: row.max_drawdown,
        win_rate: row.win_rate,
        avg_win_pct: row.meta?.metrics_extra?.avg_win_pct,
        avg_loss_pct: row.meta?.metrics_extra?.avg_loss_pct,
        time_in_market: row.meta?.metrics_extra?.time_in_market,
        profit_factor: row.meta?.metrics_extra?.profit_factor,
        num_trades: row.num_trades,
        total_costs: row.total_costs,
        trades: row.meta?.trades || [],
        validation: row.meta?.validation || null,
        oos_window: row.meta?.oos_window || null,
        halted: row.meta?.risk?.halted || false,
        halt_reason: row.meta?.risk?.halt_reason || null,
        stop_exits: row.meta?.risk?.stop_exits || 0,
        commission_bps: row.params?.commission_bps,
        slippage_bps: row.params?.slippage_bps,
        position_size_pct: row.params?.position_size_pct ?? row.meta?.costs?.position_size_pct,
      });
    } catch (e) {
      setError(e?.message || "could not open run");
    }
  };

  return (
    <div className="run-history">
      <div className="run-history-head">
        <span className="label-row">
          run history
          <InfoTip text="saved paper runs click one to reload its charts" />
        </span>
        <button type="button" className="ghost-btn" onClick={load} disabled={loading}>
          refresh
        </button>
      </div>
      {error && <div className="run-history-err">{error}</div>}
      {!runs.length && !loading && <p className="run-history-empty">no saved runs yet</p>}
      <ul className="run-list">
        {runs.map((r) => (
          <li key={r.id}>
            <button type="button" className="run-item" onClick={() => openRun(r.id)}>
              <span className="run-ticker">{r.ticker}</span>
              <span className="run-meta">
                {r.strategy} · {r.total_return?.toFixed?.(1) ?? r.total_return}%
              </span>
              <span className="run-date">{String(r.created_at).slice(0, 10)}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
