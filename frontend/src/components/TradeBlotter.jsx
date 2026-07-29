// closed trades table - one row per round trip

import InfoTip from "./InfoTip.jsx";
import "./TradeBlotter.css";

function fmtPct(x) {
  if (x == null || Number.isNaN(x)) return "-";
  const n = Number(x);
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}

function fmtPx(x) {
  if (x == null || Number.isNaN(x)) return "-";
  return Number(x).toFixed(2);
}

export default function TradeBlotter({ trades }) {
  const rows = Array.isArray(trades) ? trades : [];
  if (!rows.length) {
    return (
      <div className="blotter">
        <div className="blotter-head">
          <span className="label-row">
            trade blotter
            <InfoTip text="list of closed buy then sell cycles for this run" />
          </span>
        </div>
        <p className="blotter-empty">no closed trades this run</p>
      </div>
    );
  }

  return (
    <div className="blotter">
      <div className="blotter-head">
        <span className="label-row">
          trade blotter · {rows.length}
          <InfoTip text="each row is one closed trade entry exit pnl and why we exited" />
        </span>
      </div>
      <div className="blotter-scroll">
        <table className="blotter-table">
          <thead>
            <tr>
              <th>
                <span className="label-row">
                  entry
                  <InfoTip text="day we bought" />
                </span>
              </th>
              <th>
                <span className="label-row">
                  exit
                  <InfoTip text="day we sold" />
                </span>
              </th>
              <th>
                <span className="label-row">
                  entry px
                  <InfoTip text="fill price on the buy incl slippage" />
                </span>
              </th>
              <th>
                <span className="label-row">
                  exit px
                  <InfoTip text="fill price on the sell incl slippage" />
                </span>
              </th>
              <th>
                <span className="label-row">
                  pnl
                  <InfoTip text="percent gain or loss on that trade" />
                </span>
              </th>
              <th>
                <span className="label-row">
                  reason
                  <InfoTip text="signal stop loss or max drawdown halt" />
                </span>
              </th>
              <th>
                <span className="label-row">
                  fees
                  <InfoTip text="commission paid on that round trip" />
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t, i) => {
              const pnl = Number(t.pnl_pct);
              const tone = pnl > 0 ? "good" : pnl < 0 ? "bad" : "neutral";
              return (
                <tr key={`${t.entry_date}-${t.exit_date}-${i}`}>
                  <td>{t.entry_date}</td>
                  <td>{t.exit_date}</td>
                  <td>{fmtPx(t.entry_price)}</td>
                  <td>{fmtPx(t.exit_price)}</td>
                  <td className={`tone-${tone}`}>{fmtPct(t.pnl_pct)}</td>
                  <td>{t.reason}</td>
                  <td>${Number(t.fees ?? 0).toFixed(2)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
