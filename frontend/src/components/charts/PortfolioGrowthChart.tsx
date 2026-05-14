"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend,
} from "recharts";
import { useMemo } from "react";

interface GrowthPoint {
  date: string;
  invested_amount: number;
  current_value: number;
}

interface MarketEvent {
  date: string;
  short_label: string;
  type: string;
}

interface Props {
  data: GrowthPoint[];
  events?: MarketEvent[];
}

const EVENT_COLORS: Record<string, string> = {
  crash: "#ef4444",
  recovery: "#22c55e",
  policy: "#f59e0b",
  political: "#a78bfa",
  other: "#94a3b8",
};

function formatINR(value: number) {
  if (value >= 1_00_00_000) return `₹${(value / 1_00_00_000).toFixed(1)}Cr`;
  if (value >= 1_00_000) return `₹${(value / 1_00_000).toFixed(1)}L`;
  if (value >= 1_000) return `₹${(value / 1_000).toFixed(1)}K`;
  return `₹${value.toFixed(0)}`;
}

function formatDateLabel(str: string) {
  const d = new Date(str);
  return d.toLocaleDateString("en-IN", { month: "short", year: "2-digit" });
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  const invested = payload.find((p: any) => p.dataKey === "invested_amount");
  const current = payload.find((p: any) => p.dataKey === "current_value");
  const gain = (current?.value ?? 0) - (invested?.value ?? 0);
  const gainPct =
    invested?.value > 0 ? ((gain / invested.value) * 100).toFixed(2) : null;

  return (
    <div className="glass-card px-4 py-3 text-xs shadow-2xl min-w-[180px]">
      <p className="text-slate-400 mb-2 font-medium">
        {new Date(label).toLocaleDateString("en-IN", {
          day: "numeric",
          month: "short",
          year: "numeric",
        })}
      </p>
      <div className="space-y-1.5">
        <div className="flex justify-between gap-4">
          <span className="text-indigo-400">Invested</span>
          <span className="text-slate-50 font-semibold">
            {formatINR(invested?.value ?? 0)}
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-emerald-400">Current Value</span>
          <span className="text-slate-50 font-semibold">
            {formatINR(current?.value ?? 0)}
          </span>
        </div>
        {gainPct !== null && (
          <div className="flex justify-between gap-4 border-t border-white/10 pt-1.5 mt-1.5">
            <span className="text-slate-500">Gain/Loss</span>
            <span className={gain >= 0 ? "text-emerald-400 font-semibold" : "text-red-400 font-semibold"}>
              {gain >= 0 ? "+" : ""}{formatINR(gain)} ({gainPct}%)
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default function PortfolioGrowthChart({ data, events = [] }: Props) {
  // Filter events that fall within the data range
  const dateRange = useMemo(() => {
    if (!data.length) return { min: "", max: "" };
    return { min: data[0].date, max: data[data.length - 1].date };
  }, [data]);

  const relevantEvents = useMemo(
    () =>
      events.filter(
        (e) => e.date >= dateRange.min && e.date <= dateRange.max
      ),
    [events, dateRange]
  );

  if (!data.length) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-600 text-sm">
        No portfolio data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={320}>
      <AreaChart data={data} margin={{ top: 10, right: 16, left: 16, bottom: 0 }}>
        <defs>
          <linearGradient id="investedGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#6366f1" stopOpacity={0.25} />
            <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="currentGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
          </linearGradient>
        </defs>

        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />

        <XAxis
          dataKey="date"
          tickFormatter={formatDateLabel}
          tick={{ fontSize: 11, fill: "#64748b" }}
          tickLine={false}
          axisLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          tickFormatter={formatINR}
          tick={{ fontSize: 11, fill: "#64748b" }}
          tickLine={false}
          axisLine={false}
          width={60}
        />

        <Tooltip content={<CustomTooltip />} />
        <Legend
          formatter={(val) =>
            val === "invested_amount" ? "Invested" : "Current Value"
          }
          wrapperStyle={{ fontSize: 12, color: "#94a3b8" }}
        />

        {/* Market event reference lines */}
        {relevantEvents.map((event) => (
          <ReferenceLine
            key={event.date}
            x={event.date}
            stroke={EVENT_COLORS[event.type] || EVENT_COLORS.other}
            strokeDasharray="4 2"
            strokeOpacity={0.7}
            label={{
              value: event.short_label,
              position: "top",
              fontSize: 9,
              fill: EVENT_COLORS[event.type] || EVENT_COLORS.other,
              opacity: 0.85,
            }}
          />
        ))}

        <Area
          type="monotone"
          dataKey="invested_amount"
          stroke="#6366f1"
          strokeWidth={2}
          fill="url(#investedGrad)"
          dot={false}
          activeDot={{ r: 4, fill: "#6366f1" }}
          animationDuration={800}
        />
        <Area
          type="monotone"
          dataKey="current_value"
          stroke="#22c55e"
          strokeWidth={2.5}
          fill="url(#currentGrad)"
          dot={false}
          activeDot={{ r: 5, fill: "#22c55e" }}
          animationDuration={1000}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
