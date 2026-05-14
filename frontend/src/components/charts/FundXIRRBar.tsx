"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
  LabelList,
} from "recharts";

interface FundXIRR {
  fund_name: string;
  xirr_pct: number | null;
  current_value: number;
  invested: number;
}

interface Props {
  funds: FundXIRR[];
}

function truncateName(name: string, max = 28) {
  return name.length > max ? name.slice(0, max) + "…" : name;
}

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload as FundXIRR;
  const xirr = d.xirr_pct;
  return (
    <div className="glass-card px-4 py-3 text-xs min-w-[200px] shadow-2xl">
      <p className="text-slate-50 font-semibold mb-2 leading-snug">{d.fund_name}</p>
      <div className="space-y-1">
        <div className="flex justify-between gap-4">
          <span className="text-slate-400">XIRR</span>
          <span className={`font-bold ${xirr != null && xirr >= 0 ? "text-emerald-400" : "text-red-400"}`}>
            {xirr != null ? `${xirr >= 0 ? "+" : ""}${xirr.toFixed(2)}%` : "N/A"}
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-slate-400">Invested</span>
          <span className="text-slate-200">
            ₹{d.invested.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-slate-400">Current</span>
          <span className="text-slate-200">
            ₹{d.current_value.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
          </span>
        </div>
      </div>
    </div>
  );
};

export default function FundXIRRBar({ funds }: Props) {
  // Only show funds with a valid XIRR; sort best → worst
  const data = [...funds]
    .filter((f) => f.xirr_pct !== null)
    .sort((a, b) => (b.xirr_pct ?? 0) - (a.xirr_pct ?? 0))
    .map((f) => ({ ...f, short_name: truncateName(f.fund_name) }));

  const naFunds = funds.filter((f) => f.xirr_pct === null);

  if (!data.length) {
    return (
      <div className="h-56 flex items-center justify-center text-slate-600 text-sm">
        No XIRR data available
      </div>
    );
  }

  const chartHeight = Math.max(240, data.length * 44);

  return (
    <div>
      <ResponsiveContainer width="100%" height={chartHeight}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 60, left: 4, bottom: 4 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            horizontal={false}
            stroke="rgba(255,255,255,0.05)"
          />
          <XAxis
            type="number"
            tickFormatter={(v) => `${v}%`}
            tick={{ fontSize: 10, fill: "#64748b" }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            type="category"
            dataKey="short_name"
            tick={{ fontSize: 10, fill: "#94a3b8" }}
            tickLine={false}
            axisLine={false}
            width={120}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
          <ReferenceLine x={0} stroke="rgba(255,255,255,0.2)" />
          <Bar dataKey="xirr_pct" radius={[0, 4, 4, 0]} maxBarSize={28} animationDuration={700}>
            {data.map((entry, index) => (
              <Cell
                key={index}
                fill={
                  (entry.xirr_pct ?? 0) >= 0
                    ? "url(#xirrPositive)"
                    : "url(#xirrNegative)"
                }
              />
            ))}
            <LabelList
              dataKey="xirr_pct"
              position="right"
              formatter={(v: unknown) => {
                const n = Number(v);
                return isNaN(n) ? "" : `${n >= 0 ? "+" : ""}${n.toFixed(1)}%`;
              }}
              style={{ fontSize: 10, fill: "#94a3b8" }}
            />
          </Bar>
          <defs>
            <linearGradient id="xirrPositive" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#10b981" stopOpacity={0.7} />
              <stop offset="100%" stopColor="#34d399" stopOpacity={0.9} />
            </linearGradient>
            <linearGradient id="xirrNegative" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#ef4444" stopOpacity={0.7} />
              <stop offset="100%" stopColor="#f87171" stopOpacity={0.9} />
            </linearGradient>
          </defs>
        </BarChart>
      </ResponsiveContainer>

      {naFunds.length > 0 && (
        <p className="text-xs text-slate-600 mt-3 px-1">
          {naFunds.length} fund{naFunds.length > 1 ? "s" : ""} excluded (insufficient data for XIRR)
        </p>
      )}
    </div>
  );
}
