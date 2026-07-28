// ml: reference line at oos start so train vs test is visible

import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import "./PerformanceChart.css";

function mergeCurves(equityCurve, buyHoldCurve, zeroEquity) {
  const bhMap = new Map((buyHoldCurve || []).map((x) => [x.date, x.value]));
  const zMap = new Map((zeroEquity || []).map((x) => [x.date, x.value]));
  return (equityCurve || []).map((row) => ({
    date: row.date,
    portfolio: row.value,
    benchmark: bhMap.get(row.date),
    zeroCost: zMap.has(row.date) ? zMap.get(row.date) : undefined,
  }));
}

function formatMoney(v) {
  if (v == null || Number.isNaN(v)) return "-";
  return `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function formatTickDate(d) {
  if (!d || typeof d !== "string") return "";
  const [y, m] = d.split("-");
  return `${m}/${y?.slice(2) ?? ""}`;
}

export default function PerformanceChart({
  equityCurve,
  buyHoldCurve,
  zeroCostEquity,
  showZeroCost,
  oosWindow,
}) {
  const data = mergeCurves(equityCurve, buyHoldCurve, showZeroCost ? zeroCostEquity : null);
  const uid = "perf-grad";
  const oosStart = oosWindow?.oos_start;
  const trainEnd = oosWindow?.train_end;

  return (
    <div className="chart-card">
      <div className="chart-title-row">
        <div className="chart-title">equity vs buy &amp; hold</div>
        {oosWindow && (
          <span className="oos-badge" title={oosWindow.label}>
            OOS only
            {oosStart ? ` · from ${oosStart}` : ""}
          </span>
        )}
      </div>
      {trainEnd && oosStart && (
        <p className="chart-caption">
          train ends {trainEnd} · out-of-sample {oosStart}
          {oosWindow?.oos_end ? ` → ${oosWindow.oos_end}` : ""} · in-sample bars are not traded
        </p>
      )}
      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id={`${uid}-p`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#00ff88" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#00ff88" stopOpacity={0} />
              </linearGradient>
              <linearGradient id={`${uid}-b`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#888888" stopOpacity={0.28} />
                <stop offset="100%" stopColor="#888888" stopOpacity={0} />
              </linearGradient>
              <linearGradient id={`${uid}-z`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#ffcc66" stopOpacity={0.22} />
                <stop offset="100%" stopColor="#ffcc66" stopOpacity={0} />
              </linearGradient>
            </defs>
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
              tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
              stroke="#2a2a2a"
              width={48}
            />
            <Tooltip
              contentStyle={{
                background: "#111111",
                border: "1px solid #2a2a2a",
                borderRadius: 8,
                fontSize: 12,
                fontFamily: "JetBrains Mono, monospace",
              }}
              labelStyle={{ color: "#b0b0b0" }}
              formatter={(value, name) => {
                const labels = {
                  portfolio: "strategy (with costs)",
                  benchmark: "buy & hold",
                  zeroCost: "strategy (zero costs)",
                };
                return [formatMoney(value), labels[name] || name];
              }}
              labelFormatter={(label) => label}
            />
            {oosStart && (
              <>
                <ReferenceArea
                  x1={data[0]?.date}
                  x2={oosStart}
                  strokeOpacity={0}
                  fill="#ffffff"
                  fillOpacity={0.03}
                  ifOverflow="extendDomain"
                />
                <ReferenceLine
                  x={oosStart}
                  stroke="#00ff88"
                  strokeDasharray="4 4"
                  label={{
                    value: "OOS →",
                    fill: "#00ff88",
                    fontSize: 10,
                    position: "insideTopRight",
                  }}
                />
              </>
            )}
            <Area
              type="monotone"
              dataKey="benchmark"
              stroke="#888888"
              strokeWidth={1.2}
              fill={`url(#${uid}-b)`}
              name="benchmark"
              isAnimationActive
            />
            {showZeroCost && (
              <Area
                type="monotone"
                dataKey="zeroCost"
                stroke="#ffcc66"
                strokeWidth={1.2}
                fill={`url(#${uid}-z)`}
                name="zeroCost"
                isAnimationActive
              />
            )}
            <Area
              type="monotone"
              dataKey="portfolio"
              stroke="#00ff88"
              strokeWidth={1.5}
              fill={`url(#${uid}-p)`}
              name="portfolio"
              isAnimationActive
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
