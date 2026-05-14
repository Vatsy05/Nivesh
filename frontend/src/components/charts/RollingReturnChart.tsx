"use client";

import { useState } from "react";
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

type Window = "1Y" | "3Y" | "5Y";

interface RollingPoint {
  date: string;
  return_pct: number;
}

interface WindowSummary {
  min: number;
  max: number;
  median: number;
  current: number;
}

interface Props {
  series: Record<Window, RollingPoint[]>;
  summary: Record<Window, WindowSummary | null>;
  schemeName?: string;
}

const WINDOW_LABELS: Record<Window, string> = {
  "1Y": "1 Year",
  "3Y": "3 Year",
  "5Y": "5 Year",
};

function formatDate(str: string) {
  const d = new Date(str);
  return d.toLocaleDateString("en-IN", { month: "short", year: "2-digit" });
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass-card px-3 py-2 text-xs shadow-2xl">
      <p className="text-slate-400 mb-1">{formatDate(label)}</p>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex justify-between gap-3">
          <span style={{ color: p.color }}>{p.name}</span>
          <span className="text-slate-50 font-semibold">
            {p.value >= 0 ? "+" : ""}{Number(p.value).toFixed(2)}%
          </span>
        </div>
      ))}
    </div>
  );
};

export default function RollingReturnChart({ series, summary, schemeName }: Props) {
  const [activeWindow, setActiveWindow] = useState<Window>("1Y");

  const currentSeries = series[activeWindow] ?? [];
  const currentSummary = summary[activeWindow];

  // For ComposedChart, build data with min/max/median columns
  const chartData = currentSeries.map((pt) => ({
    date: pt.date,
    return_pct: pt.return_pct,
  }));

  const isEmpty = chartData.length === 0;

  return (
    <div>
      {/* Window selector */}
      <div className="flex items-center gap-2 mb-4">
        {(["1Y", "3Y", "5Y"] as Window[]).map((w) => (
          <button
            key={w}
            onClick={() => setActiveWindow(w)}
            disabled={!series[w]?.length}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all disabled:opacity-30 disabled:cursor-not-allowed ${
              activeWindow === w
                ? "bg-indigo-500/20 text-indigo-400 border border-indigo-500/40"
                : "bg-slate-800/40 text-slate-500 border border-white/5 hover:border-white/10"
            }`}
          >
            {WINDOW_LABELS[w]}
          </button>
        ))}
      </div>

      {/* Summary pills */}
      {currentSummary && (
        <div className="grid grid-cols-4 gap-2 mb-4">
          {[
            { label: "Min", value: currentSummary.min, color: "text-red-400" },
            { label: "Median", value: currentSummary.median, color: "text-amber-400" },
            { label: "Current", value: currentSummary.current, color: "text-indigo-400" },
            { label: "Max", value: currentSummary.max, color: "text-emerald-400" },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-slate-900/40 rounded-xl p-2 text-center border border-white/5">
              <div className={`text-sm font-bold ${color}`}>
                {value >= 0 ? "+" : ""}{value.toFixed(1)}%
              </div>
              <div className="text-[10px] text-slate-600 mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      )}

      {isEmpty ? (
        <div className="h-48 flex items-center justify-center text-slate-600 text-sm">
          Insufficient NAV history for {WINDOW_LABELS[activeWindow]} rolling returns
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <ComposedChart data={chartData} margin={{ top: 4, right: 8, left: 4, bottom: 0 }}>
            <defs>
              <linearGradient id="rollingGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              tick={{ fontSize: 10, fill: "#64748b" }}
              tickLine={false}
              axisLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tickFormatter={(v) => `${v}%`}
              tick={{ fontSize: 10, fill: "#64748b" }}
              tickLine={false}
              axisLine={false}
              width={48}
            />
            <Tooltip content={<CustomTooltip />} />

            {/* Zero reference */}
            <Line
              type="monotone"
              dataKey={() => 0}
              stroke="rgba(255,255,255,0.1)"
              strokeWidth={1}
              dot={false}
              legendType="none"
            />

            {/* Rolling return area */}
            <Area
              type="monotone"
              dataKey="return_pct"
              name={`${WINDOW_LABELS[activeWindow]} Rolling Return`}
              stroke="#6366f1"
              strokeWidth={1.5}
              fill="url(#rollingGrad)"
              dot={false}
              animationDuration={600}
            />
          </ComposedChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
