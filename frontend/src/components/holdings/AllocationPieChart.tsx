"use client";

import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
} from "recharts";

interface HoldingItem {
  fund_name:     string;
  current_value: number;
  invested_amount: number;
}

interface Props {
  holdings: HoldingItem[];
  loading?: boolean;
}

const PALETTE = [
  "#6366f1", "#d946ef", "#22c55e", "#f59e0b", "#38bdf8",
  "#f87171", "#a78bfa", "#34d399", "#fb923c", "#e879f9",
];

function Skeleton({ className }: { className?: string }) {
  return <div className={`animate-pulse bg-slate-700/60 rounded-full ${className}`} />;
}

function shortName(name: string): string {
  // Abbreviate long fund names
  return name
    .replace(/Mutual Fund/gi, "MF")
    .replace(/Direct Plan/gi, "Dir")
    .replace(/Growth/gi, "Gr")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 28);
}

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div className="glass-card px-4 py-3 text-sm">
      <p className="text-slate-50 font-semibold mb-1">{d.name}</p>
      <p className="text-slate-300">₹{d.value.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</p>
      <p className="text-slate-400">{d.payload.pct.toFixed(1)}% of portfolio</p>
    </div>
  );
};

export default function AllocationPieChart({ holdings, loading }: Props) {
  if (loading) {
    return (
      <div className="glass-card p-6">
        <div className="animate-pulse bg-slate-700/60 rounded h-4 w-36 mb-4" />
        <div className="flex justify-center">
          <Skeleton className="w-48 h-48" />
        </div>
      </div>
    );
  }

  const total = holdings.reduce((s, h) => s + h.current_value, 0);
  if (total === 0) {
    return (
      <div className="glass-card p-6 flex flex-col items-center justify-center min-h-[260px]">
        <p className="text-slate-400 text-sm">No holdings data</p>
      </div>
    );
  }

  const data = holdings
    .filter(h => h.current_value > 0)
    .sort((a, b) => b.current_value - a.current_value)
    .map((h, i) => ({
      name:  shortName(h.fund_name),
      value: Math.round(h.current_value),
      pct:   (h.current_value / total) * 100,
      color: PALETTE[i % PALETTE.length],
    }));

  return (
    <div className="glass-card p-6">
      <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
        Allocation
      </h3>

      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius={55}
            outerRadius={85}
            paddingAngle={2}
            strokeWidth={0}
          >
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.color} opacity={0.9} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
        </PieChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="mt-3 space-y-1.5">
        {data.map((d, i) => (
          <div key={i} className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span
                className="w-2 h-2 rounded-full flex-shrink-0"
                style={{ background: d.color }}
              />
              <span className="text-slate-400 truncate max-w-[140px]">{d.name}</span>
            </div>
            <span className="text-slate-300 font-medium ml-2">{d.pct.toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
