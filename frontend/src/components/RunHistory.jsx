// sqlite history from /api/runs - click to reload charts

import { useCallback, useEffect, useState } from "react";
import { fetchRun, fetchRuns } from "../api/client.js";
import InfoTip from "./InfoTip.jsx";
import "./RunHistory.css";

export default function RunHistory({ onSelect, refreshKey }) {
  const [runs, setRuns] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [tickerFilter, setTickerFilter] = useState("");
  const [strategyFilter, setStrategyFilter] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchRuns({
        limit: 12,
        ticker: tickerFilter.trim() || undefined,
        strategy: strategyFilter || undefined,
      });
      setRuns(data.runs || []);
    } catch (e) {
      setError(e?.message || "could not load runs");
      setRuns([]);
    } finally {
      setLoading(false);
    }
  }, [tickerFilter, strategyFilter]);

  useEffect(() => {
    // refreshKey changes after each successful backtest
    load();
  }, [load, refreshKey]);

  const openRun = async (id) => {
    try {
      const row = await fetchRun(id);
      if (!row.equity_curve) {
        setError("this older run has no stored equity curve - re-run to refresh history");
        return;
      }
      const meta = row.meta || {};
      // reshape sqlite row into the same shape as a fresh /api/backtest response
      onSelect?.({
        run_id: row.id,
        equity_curve: row.equity_curve,
        buy_hold_curve: row.buy_hold_curve || [],
        price_series: meta.price_series || [],
        equity_curve_zero_cost: meta.equity_curve_zero_cost || null,
        buy_hold_curve_zero_cost: meta.buy_hold_curve_zero_cost || null,
        zero_cost: meta.zero_cost || null,
        total_return: row.total_return,
        sharpe_ratio: row.sharpe_ratio,
        // extras were stuffed into meta at save time
        sortino_ratio: meta.metrics_extra?.sortino_ratio,
        max_drawdown: row.max_drawdown,
        win_rate: row.win_rate,
        avg_win_pct: meta.metrics_extra?.avg_win_pct,
        avg_loss_pct: meta.metrics_extra?.avg_loss_pct,
        time_in_market: meta.metrics_extra?.time_in_market,
        profit_factor: meta.metrics_extra?.profit_factor,
        num_trades: row.num_trades,
        total_costs: row.total_costs,
        trades: meta.trades || [],
        validation: meta.validation || null,
        oos_window: meta.oos_window || null,
        halted: meta.risk?.halted || false,
        halt_reason: meta.risk?.halt_reason || null,
        stop_exits: meta.risk?.stop_exits || 0,
        commission_bps: row.params?.commission_bps,
        slippage_bps: row.params?.slippage_bps,
        position_size_pct: row.params?.position_size_pct ?? meta.costs?.position_size_pct,
        desk_note: meta.desk_note || "",
        meta,
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
      <div className="run-history-filters">
        <input
          type="text"
          className="run-filter-input"
          placeholder="ticker"
          value={tickerFilter}
          onChange={(e) => setTickerFilter(e.target.value)}
          aria-label="filter by ticker"
        />
        <select
          className="run-filter-select"
          value={strategyFilter}
          onChange={(e) => setStrategyFilter(e.target.value)}
          aria-label="filter by strategy"
        >
          <option value="">all</option>
          <option value="ma">ma</option>
          <option value="rsi">rsi</option>
          <option value="ml">ml</option>
        </select>
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
