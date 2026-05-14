"use client";

import { TrendingUp, TrendingDown, Wallet, BarChart2, Zap, ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";

interface SummaryData {
  total_value:      number;
  total_invested:   number;
  total_pnl:        number;
  daily_gain:       number;
  daily_gain_pct:   number;
  xirr_pct:         number | null;
  abs_return_pct:   number | null;
  num_funds:        number;
}

interface Props {
  data: SummaryData | null;
  loading?: boolean;
}

function fmt(n: number, decimals = 2): string {
  if (Math.abs(n) >= 10_000_000) return `₹${(n / 10_000_000).toFixed(2)}Cr`;
  if (Math.abs(n) >= 100_000)    return `₹${(n / 100_000).toFixed(2)}L`;
  return `₹${n.toLocaleString("en-IN", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`;
}

function GainBadge({ value, pct, size = "md" }: { value: number; pct?: number; size?: "sm" | "md" | "lg" }) {
  const pos = value >= 0;
  const zero = Math.abs(value) < 0.01;
  const color = zero ? "text-slate-400" : pos ? "text-emerald-400" : "text-red-400";
  const Icon = zero ? Minus : pos ? ArrowUpRight : ArrowDownRight;
  const sizes = { sm: "text-sm", md: "text-lg", lg: "text-2xl" };

  return (
    <span className={`flex items-center gap-1 font-semibold ${color} ${sizes[size]}`}>
      <Icon className="w-4 h-4 flex-shrink-0" />
      {pos && !zero ? "+" : ""}{fmt(value)}
      {pct !== undefined && (
        <span className="text-sm font-normal opacity-80">
          ({pos && !zero ? "+" : ""}{pct.toFixed(2)}%)
        </span>
      )}
    </span>
  );
}

function Skeleton({ className }: { className?: string }) {
  return <div className={`animate-pulse bg-slate-700/60 rounded-lg ${className}`} />;
}

export default function HoldingsSummaryBar({ data, loading }: Props) {
  if (loading || !data) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="glass-card p-5">
            <Skeleton className="h-3 w-24 mb-3" />
            <Skeleton className="h-8 w-32 mb-2" />
            <Skeleton className="h-3 w-20" />
          </div>
        ))}
      </div>
    );
  }

  const pnlPositive = data.total_pnl >= 0;
  const absRet = data.abs_return_pct ?? (data.total_invested > 0 ? (data.total_pnl / data.total_invested) * 100 : 0);

  const cards = [
    {
      label: "Current Value",
      icon: <Wallet className="w-4 h-4 text-indigo-400" />,
      main: <span className="text-2xl font-bold text-slate-50">{fmt(data.total_value)}</span>,
      sub: <span className="text-xs text-slate-500">Invested {fmt(data.total_invested)}</span>,
      accent: "from-indigo-500/20 to-transparent",
      border: "border-indigo-500/20",
    },
    {
      label: "Total Returns",
      icon: pnlPositive
        ? <TrendingUp className="w-4 h-4 text-emerald-400" />
        : <TrendingDown className="w-4 h-4 text-red-400" />,
      main: <GainBadge value={data.total_pnl} pct={absRet} size="md" />,
      sub: <span className="text-xs text-slate-500">{data.num_funds} active fund{data.num_funds !== 1 ? "s" : ""}</span>,
      accent: pnlPositive ? "from-emerald-500/10 to-transparent" : "from-red-500/10 to-transparent",
      border: pnlPositive ? "border-emerald-500/20" : "border-red-500/20",
    },
    {
      label: "Today's Gain",
      icon: data.daily_gain >= 0
        ? <ArrowUpRight className="w-4 h-4 text-sky-400" />
        : <ArrowDownRight className="w-4 h-4 text-orange-400" />,
      main: <GainBadge value={data.daily_gain} pct={data.daily_gain_pct} size="md" />,
      sub: <span className="text-xs text-slate-500">vs yesterday's close</span>,
      accent: "from-sky-500/10 to-transparent",
      border: "border-sky-500/20",
    },
    {
      label: "XIRR",
      icon: <Zap className="w-4 h-4 text-fuchsia-400" />,
      main: data.xirr_pct != null
        ? <span className={`text-2xl font-bold ${data.xirr_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
            {data.xirr_pct >= 0 ? "+" : ""}{data.xirr_pct.toFixed(2)}%
          </span>
        : <span className="text-slate-500 text-lg">Calculating…</span>,
      sub: <span className="text-xs text-slate-500">Annualised IRR</span>,
      accent: "from-fuchsia-500/10 to-transparent",
      border: "border-fuchsia-500/20",
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      {cards.map((card) => (
        <div
          key={card.label}
          className={`glass-card p-5 border ${card.border} bg-gradient-to-br ${card.accent} animate-fade-in`}
        >
          <div className="flex items-center gap-2 mb-2">
            {card.icon}
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{card.label}</span>
          </div>
          <div className="mb-1">{card.main}</div>
          <div>{card.sub}</div>
        </div>
      ))}
    </div>
  );
}
