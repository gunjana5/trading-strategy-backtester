// side-by-side ma / rsi / ml under the same costs

import InfoTip from "./InfoTip.jsx";
import "./CompareTable.css";

const LABELS = { ma: "moving average", rsi: "rsi", ml: "ml" };

function fmt(n, digits = 2) {
  if (n == null || Number.isNaN(Number(n))) return "-";
  return Number(n).toFixed(digits);
}

function fmtPct(n) {
  if (n == null || Number.isNaN(Number(n))) return "-";
  return `${Number(n).toFixed(2)}%`;
}

export default function CompareTable({ data }) {
  if (!data?.rows?.length) return null;
  const { ticker, start, end, costs, rows } = data;
  // highlight the strategy with the best total return (ties ok)
  const bestReturn = rows.reduce((best, r) => {
    const v = Number(r.total_return);
    if (Number.isNaN(v)) return best;
    return best == null || v > best ? v : best;
  }, null);

  return (
    <section className="compare-root fade-in">
      <div className="compare-head">
        <span className="pill">
          <span className="label-row">
            compare
            <InfoTip text="same ticker dates and costs - ma vs rsi vs ml so you can see which held up" />
          </span>
        </span>
        <span className="subtle">
          {ticker} · {start} → {end} · costs {costs?.commission_bps}/{costs?.slippage_bps} bps ·
          size {costs?.position_size_pct}%
        </span>
      </div>
      <div className="compare-scroll">
        <table className="compare-table">
          <thead>
            <tr>
              <th>strategy</th>
              <th>return</th>
              <th>sharpe</th>
              <th>sortino</th>
              <th>max dd</th>
              <th>win rate</th>
              <th>trades</th>
              <th>costs</th>
              <th>time in mkt</th>
              <th>oos acc</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const isBest =
                bestReturn != null && Number(r.total_return) === bestReturn;
              return (
                <tr key={r.strategy} className={isBest ? "is-best" : undefined}>
                  <td className="strat-name">
                    {LABELS[r.strategy] || r.strategy}
                    {isBest ? <span className="best-tag">best return</span> : null}
                  </td>
                  <td>{fmtPct(r.total_return)}</td>
                  <td>{fmt(r.sharpe_ratio)}</td>
                  <td>{fmt(r.sortino_ratio)}</td>
                  <td>{fmtPct(r.max_drawdown)}</td>
                  <td>{fmtPct(r.win_rate)}</td>
                  <td>{r.num_trades ?? "-"}</td>
                  <td>${fmt(r.total_costs)}</td>
                  <td>{fmtPct(r.time_in_market)}</td>
                  <td>
                    {r.mean_oos_accuracy == null
                      ? "-"
                      : `${(Number(r.mean_oos_accuracy) * 100).toFixed(1)}%`}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
