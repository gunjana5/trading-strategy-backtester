// build a csv blob from one backtest result

function esc(v) {
  const s = v == null ? "" : String(v);
  if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

export function downloadRunCsv(data) {
  if (!data) return;
  const lines = [];
  lines.push("section,key,value");
  const metrics = [
    ["run_id", data.run_id],
    ["total_return_pct", data.total_return],
    ["sharpe_ratio", data.sharpe_ratio],
    ["sortino_ratio", data.sortino_ratio],
    ["max_drawdown_pct", data.max_drawdown],
    ["win_rate_pct", data.win_rate],
    ["avg_win_pct", data.avg_win_pct],
    ["avg_loss_pct", data.avg_loss_pct],
    ["time_in_market_pct", data.time_in_market],
    ["profit_factor", data.profit_factor],
    ["num_trades", data.num_trades],
    ["total_costs", data.total_costs],
    ["commission_bps", data.commission_bps],
    ["slippage_bps", data.slippage_bps],
    ["position_size_pct", data.position_size_pct],
    ["desk_note", data.desk_note || data.meta?.desk_note || ""],
  ];
  for (const [k, v] of metrics) {
    lines.push(["metrics", k, v].map(esc).join(","));
  }

  lines.push("");
  lines.push("entry_date,exit_date,entry_price,exit_price,pnl_pct,reason,fees,shares");
  for (const t of data.trades || []) {
    lines.push(
      [
        t.entry_date,
        t.exit_date,
        t.entry_price,
        t.exit_price,
        t.pnl_pct,
        t.reason,
        t.fees,
        t.shares,
      ]
        .map(esc)
        .join(",")
    );
  }

  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `backtest-run-${data.run_id ?? "latest"}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
