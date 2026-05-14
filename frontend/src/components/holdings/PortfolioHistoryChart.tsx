"use client";

import { useState } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { RefreshCw } from "lucide-react";

interface SnapshotPoint {
  date:            string;
  invested_amount: number;
  portfolio_value: number;
  daily_pnl:       number;
  total_pnl:       number;
}

interface Props {
  data: SnapshotPoint[];
  loading?: boolean;
  onRebuild?: () => void;
}

function fmt(n: number): string {
  if (Math.abs(n) >= 10_000_000) return `₹${(n / 10_000_000).toFixed(2)}Cr`;
  if (Math.abs(n) >= 100_000)    return `₹${(n / 100_000).toFixed(2)}L`;
  return `₹${n.toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

function fmtDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-IN", {
    day: "numeric", month: "short", year: "2-digit",
  });
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  const invested = payload.find((p: any) => p.dataKey === "invested_amount");
  const value    = payload.find((p: any) => p.dataKey === "portfolio_value");
  const pnl      = (value?.value || 0) - (invested?.value || 0);
  const pnlPct   = invested?.value > 0 ? (pnl / invested.value) * 100 : 0;
  const pos      = pnl >= 0;

  return (
    <div className="glass-card px-4 py-3 text-sm min-w-[180px]">
      <p className="text-slate-400 text-xs mb-2">{fmtDate(label)}</p>
      <div className="space-y-1">
        <div className="flex justify-between gap-4">
          <span className="text-slate-400">Value</span>
          <span className="text-slate-50 font-semibold">{fmt(value?.value || 0)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-slate-400">Invested</span>
          <span className="text-slate-300">{fmt(invested?.value || 0)}</span>
        </div>
        <div className="flex justify-between gap-4 border-t border-white/10 pt-1 mt-1">
          <span className="text-slate-400">P&amp;L</span>
          <span className={`font-semibold ${pos ? "text-emerald-400" : "text-red-400"}`}>
            {pos ? "+" : ""}{fmt(pnl)} ({pnlPct.toFixed(2)}%)
          </span>
        </div>
      </div>
    </div>
  );
};

type Range = "1M" | "3M" | "6M" | "1Y" | "ALL";

function filterByRange(data: SnapshotPoint[], range: Range): SnapshotPoint[] {
  if (range === "ALL" || data.length === 0) return data;
  const days: Record<Range, number> = { "1M": 30, "3M": 90, "6M": 180, "1Y": 365, "ALL": 0 };
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - days[range]);
  return data.filter(d => new Date(d.date) >= cutoff);
}

export default function PortfolioHistoryChart({ data, loading, onRebuild }: Props) {
  const [range, setRange] = useState<Range>("ALL");

  const filtered = filterByRange(data, range);
  const lastPoint = filtered[filtered.length - 1];
  const firstPoint = filtered[0];

  const totalReturn = lastPoint
    ? lastPoint.portfolio_value - lastPoint.invested_amount
    : 0;
  const totalReturnPct = lastPoint?.invested_amount > 0
    ? (totalReturn / lastPoint.invested_amount) * 100
    : 0;
  const periodReturn = (lastPoint && firstPoint)
    ? lastPoint.portfolio_value - firstPoint.portfolio_value
    : 0;

  const isProfit = totalReturn >= 0;

  const RANGES: Range[] = ["1M", "3M", "6M", "1Y", "ALL"];

  return (
    <div className="glass-card p-6">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
            Portfolio Growth
          </h3>
          {lastPoint && (
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-2xl font-bold text-slate-50">
                {fmt(lastPoint.portfolio_value)}
              </span>
              <span className={`text-sm font-medium ${isProfit ? "text-emerald-400" : "text-red-400"}`}>
                {isProfit ? "+" : ""}{fmt(totalReturn)} ({totalReturnPct.toFixed(2)}%)
              </span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Range selector */}
          <div className="flex gap-1">
            {RANGES.map(r => (
              <button
                key={r}
                onClick={() => setRange(r)}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                  range === r
                    ? "bg-indigo-500/30 text-indigo-300 border border-indigo-500/40"
                    : "text-slate-500 hover:text-slate-300 hover:bg-white/5"
                }`}
              >
                {r}
              </button>
            ))}
          </div>
          {onRebuild && (
            <button
              onClick={onRebuild}
              title="Rebuild history from NAV data"
              className="p-1.5 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-white/5 transition-all"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <div className="h-64 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full mx-auto mb-2" />
            <p className="text-slate-500 text-xs">Computing historical valuations…</p>
            <p className="text-slate-600 text-xs mt-1">First load may take 15–30s</p>
          </div>
        </div>
      ) : filtered.length < 2 ? (
        <div className="h-64 flex items-center justify-center">
          <div className="text-center">
            <p className="text-slate-500 text-sm">
              {data.length === 0
                ? "No history yet. Click ↻ to compute from your transactions."
                : "Not enough data for this range."}
            </p>
          </div>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={256}>
          <AreaChart data={filtered} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="gradValue" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#6366f1" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradInvested" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#94a3b8" stopOpacity={0.12} />
                <stop offset="95%" stopColor="#94a3b8" stopOpacity={0} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />

            <XAxis
              dataKey="date"
              tickFormatter={d => new Date(d).toLocaleDateString("en-IN", { month: "short", year: "2-digit" })}
              tick={{ fontSize: 10, fill: "#64748b" }}
              axisLine={false}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tickFormatter={v => fmt(v)}
              tick={{ fontSize: 10, fill: "#64748b" }}
              axisLine={false}
              tickLine={false}
              width={72}
            />

            <Tooltip content={<CustomTooltip />} />

            <Area
              type="monotone"
              dataKey="invested_amount"
              stroke="#64748b"
              strokeWidth={1.5}
              strokeDasharray="4 3"
              fill="url(#gradInvested)"
              dot={false}
              name="Invested"
            />
            <Area
              type="monotone"
              dataKey="portfolio_value"
              stroke="#6366f1"
              strokeWidth={2}
              fill="url(#gradValue)"
              dot={false}
              name="Value"
            />
          </AreaChart>
        </ResponsiveContainer>
      )}

      {/* Legend */}
      <div className="flex items-center gap-6 mt-3 text-xs text-slate-500">
        <div className="flex items-center gap-1.5">
          <span className="w-4 h-0.5 bg-indigo-500 rounded" />
          Current Value
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-4 border-t border-dashed border-slate-500 rounded" />
          Invested
        </div>
        {filtered.length > 1 && (
          <span className="ml-auto">
            Period: {fmt(periodReturn)} {periodReturn >= 0 ? "▲" : "▼"}
          </span>
        )}
      </div>
    </div>
  );
}
