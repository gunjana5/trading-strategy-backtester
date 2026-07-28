import { useCallback, useEffect, useState } from "react";
import { fetchRun, fetchRuns } from "../api/client.js";
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
      onSelect?.({
        run_id: row.id,
        equity_curve: row.equity_curve,
        buy_hold_curve: row.buy_hold_curve || [],
        price_series: [],
        total_return: row.total_return,
        sharpe_ratio: row.sharpe_ratio,
        max_drawdown: row.max_drawdown,
        win_rate: row.win_rate,
        num_trades: row.num_trades,
        total_costs: row.total_costs,
        validation: row.meta?.validation || null,
        halted: row.meta?.risk?.halted || false,
        halt_reason: row.meta?.risk?.halt_reason || null,
        stop_exits: row.meta?.risk?.stop_exits || 0,
        commission_bps: row.params?.commission_bps,
        slippage_bps: row.params?.slippage_bps,
      });
    } catch (e) {
      setError(e?.message || "could not open run");
    }
  };

  return (
    <div className="run-history">
      <div className="run-history-head">
        <span>run history</span>
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
