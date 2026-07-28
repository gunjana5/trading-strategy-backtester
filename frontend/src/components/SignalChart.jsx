import {
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import "./SignalChart.css";

// close price plus buy/sell scatter markers (one row per day, nulls when no signal)

function BuyTriangle(props) {
  const { cx, cy } = props;
  if (cx == null || cy == null) return null;
  return (
    <path
      d={`M${cx},${cy - 7} L${cx - 6},${cy + 5} L${cx + 6},${cy + 5} Z`}
      fill="#00ff88"
      stroke="#004d33"
      strokeWidth={0.6}
    />
  );
}

function SellTriangle(props) {
  const { cx, cy } = props;
  if (cx == null || cy == null) return null;
  return (
    <path
      d={`M${cx},${cy + 7} L${cx - 6},${cy - 5} L${cx + 6},${cy - 5} Z`}
      fill="#ff5555"
      stroke="#551111"
      strokeWidth={0.6}
    />
  );
}

function formatTickDate(d) {
  if (!d || typeof d !== "string") return "";
  const [y, m] = d.split("-");
  return `${m}/${y?.slice(2) ?? ""}`;
}

function buildChartRows(priceSeries) {
  const rows = priceSeries || [];
  return rows.map((r) => ({
    date: r.date,
    close: r.close,
    signal: r.signal,
    buy: r.signal === 1 ? r.close : null,
    sell: r.signal === -1 ? r.close : null,
  }));
}

export default function SignalChart({ priceSeries }) {
  const chartData = buildChartRows(priceSeries);

  return (
    <div className="signal-card">
      <div className="signal-title">price &amp; signals</div>
      <div className="signal-legend">
        <span className="leg leg-buy">▲ buy</span>
        <span className="leg leg-sell">▼ sell</span>
      </div>
      <div className="signal-wrap">
        <ResponsiveContainer width="100%" height={260}>
          <ComposedChart data={chartData} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 6" stroke="#1a1a1a" vertical={false} />
            <XAxis
              dataKey="date"
              tick={{ fill: "#7a7a7a", fontSize: 10 }}
              tickFormatter={formatTickDate}
              minTickGap={28}
              stroke="#2a2a2a"
            />
            <YAxis
              tick={{ fill: "#7a7a7a", fontSize: 10 }}
              tickFormatter={(v) => `$${Number(v).toFixed(0)}`}
              stroke="#2a2a2a"
              width={52}
            />
            <Tooltip
              contentStyle={{
                background: "#111111",
                border: "1px solid #2a2a2a",
                borderRadius: 8,
                fontSize: 12,
                fontFamily: "JetBrains Mono, monospace",
              }}
              formatter={(value, name) => {
                if (name === "close") return [`$${Number(value).toFixed(2)}`, "close"];
                return [value, name];
              }}
              labelFormatter={(label) => label}
            />
            <Line
              type="monotone"
              dataKey="close"
              stroke="#66ffc6"
              strokeWidth={1.4}
              dot={false}
              isAnimationActive
            />
            <Scatter dataKey="buy" fill="#00ff88" shape={BuyTriangle} isAnimationActive={false} />
            <Scatter dataKey="sell" fill="#ff5555" shape={SellTriangle} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
