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
import InfoTip from "./InfoTip.jsx";
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
        <div className="chart-title">
          <span className="label-row">
            equity vs buy &amp; hold
            <InfoTip text="green is your strategy grey is buy once and sit yellow is fantasy zero fees if you toggled it" />
          </span>
        </div>
        {oosWindow && (
          <span className="oos-badge" title={oosWindow.label}>
            OOS only
            {oosStart ? ` · from ${oosStart}` : ""}
            <InfoTip text="out of sample only means we didnt trade the training bit for ml" />
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
                <stop offset="0%" stopColor="#3dcc9c" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#3dcc9c" stopOpacity={0} />
              </linearGradient>
              <linearGradient id={`${uid}-b`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#8b95a8" stopOpacity={0.28} />
                <stop offset="100%" stopColor="#8b95a8" stopOpacity={0} />
              </linearGradient>
              <linearGradient id={`${uid}-z`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f0a43a" stopOpacity={0.22} />
                <stop offset="100%" stopColor="#f0a43a" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 6" stroke="#2c3b5a" vertical={false} />
            <XAxis
              dataKey="date"
              tick={{ fill: "#7a7a7a", fontSize: 10 }}
              tickFormatter={formatTickDate}
              minTickGap={28}
              stroke="#2c3b5a"
            />
            <YAxis
              tick={{ fill: "#7a7a7a", fontSize: 10 }}
              tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
              stroke="#2c3b5a"
              width={48}
            />
            <Tooltip
              contentStyle={{
                background: "#0b1220",
                border: "1px solid #2c3b5a",
                borderRadius: 0,
                fontSize: 12,
                fontFamily: "IBM Plex Mono, monospace",
              }}
              labelStyle={{ color: "#8b95a8" }}
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
                  stroke="#3dcc9c"
                  strokeDasharray="4 4"
                  label={{
                    value: "OOS →",
                    fill: "#3dcc9c",
                    fontSize: 10,
                    position: "insideTopRight",
                  }}
                />
              </>
            )}
            <Area
              type="monotone"
              dataKey="benchmark"
              stroke="#8b95a8"
              strokeWidth={1.2}
              fill={`url(#${uid}-b)`}
              name="benchmark"
              isAnimationActive
            />
            {showZeroCost && (
              <Area
                type="monotone"
                dataKey="zeroCost"
                stroke="#f0a43a"
                strokeWidth={1.2}
                fill={`url(#${uid}-z)`}
                name="zeroCost"
                isAnimationActive
              />
            )}
            <Area
              type="monotone"
              dataKey="portfolio"
              stroke="#3dcc9c"
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
