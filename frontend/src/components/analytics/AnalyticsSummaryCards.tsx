"use client";

import { TrendingUp, TrendingDown, Wallet, BarChart3, Info } from "lucide-react";

interface SummaryData {
  total_invested: number;
  total_current_value: number;
  total_gain_loss: number;
  portfolio_xirr_pct: number | null;
  portfolio_cagr_pct: number | null;
  portfolio_absolute_return_pct: number | null;
}

interface Props {
  data: SummaryData;
}

function formatINR(value: number) {
  if (value >= 1_00_00_000) return `₹${(value / 1_00_00_000).toFixed(2)} Cr`;
  if (value >= 1_00_000) return `₹${(value / 1_00_000).toFixed(2)} L`;
  return `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

function MetricTooltip({ text }: { text: string }) {
  return (
    <div className="group relative inline-block ml-1">
      <Info className="w-3 h-3 text-slate-600 cursor-help" />
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 rounded-lg bg-slate-800 border border-white/10 shadow-xl text-[11px] text-slate-300 whitespace-nowrap z-50 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity max-w-[220px] leading-relaxed">
        {text}
        <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-px border-4 border-transparent border-t-slate-800" />
      </div>
    </div>
  );
}

export default function AnalyticsSummaryCards({ data }: Props) {
  const gainIsPositive = data.total_gain_loss >= 0;
  const xirrIsPositive = (data.portfolio_xirr_pct ?? 0) >= 0;
  const cagrIsPositive = (data.portfolio_cagr_pct ?? 0) >= 0;
  const absIsPositive = (data.portfolio_absolute_return_pct ?? 0) >= 0;

  const cards = [
    {
      label: "Total Invested",
      value: formatINR(data.total_invested),
      subtext: "Gross capital deployed",
      icon: Wallet,
      gradient: "from-indigo-500 to-indigo-400",
      shadow: "shadow-indigo-500/20",
      tooltip: "Total amount invested across all purchases (SIP + lumpsum). Does not net out redemptions.",
      valueColor: "text-slate-50",
    },
    {
      label: "Current Value",
      value: formatINR(data.total_current_value),
      subtext: gainIsPositive
        ? `+${formatINR(data.total_gain_loss)} gain`
        : `${formatINR(data.total_gain_loss)} loss`,
      icon: gainIsPositive ? TrendingUp : TrendingDown,
      gradient: gainIsPositive ? "from-emerald-500 to-emerald-400" : "from-red-500 to-red-400",
      shadow: gainIsPositive ? "shadow-emerald-500/20" : "shadow-red-500/20",
      tooltip: "Current market value = net units held × latest NAV per fund.",
      valueColor: "text-slate-50",
      subtextColor: gainIsPositive ? "text-emerald-400" : "text-red-400",
    },
    {
      label: "Portfolio XIRR",
      value:
        data.portfolio_xirr_pct != null
          ? `${xirrIsPositive ? "+" : ""}${data.portfolio_xirr_pct.toFixed(2)}%`
          : "N/A",
      subtext: "Annualised rate of return",
      icon: BarChart3,
      gradient: xirrIsPositive ? "from-fuchsia-500 to-fuchsia-400" : "from-red-500 to-red-400",
      shadow: "shadow-fuchsia-500/20",
      tooltip: "XIRR accounts for the exact timing of each SIP and investment. It is the gold standard for measuring mutual fund returns on irregular cashflows.",
      valueColor: data.portfolio_xirr_pct != null
        ? (xirrIsPositive ? "text-fuchsia-300" : "text-red-400")
        : "text-slate-500",
    },
    {
      label: "Absolute Return",
      value:
        data.portfolio_absolute_return_pct != null
          ? `${absIsPositive ? "+" : ""}${data.portfolio_absolute_return_pct.toFixed(2)}%`
          : "N/A",
      subtext:
        data.portfolio_cagr_pct != null
          ? `CAGR: ${cagrIsPositive ? "+" : ""}${data.portfolio_cagr_pct.toFixed(2)}%`
          : "CAGR: N/A",
      icon: TrendingUp,
      gradient: absIsPositive ? "from-amber-500 to-amber-400" : "from-red-500 to-red-400",
      shadow: "shadow-amber-500/20",
      tooltip: "Absolute Return = ((Current Value − Invested) / Invested) × 100. CAGR is the annualised equivalent assuming a single lump-sum investment on the first date.",
      valueColor: data.portfolio_absolute_return_pct != null
        ? (absIsPositive ? "text-amber-300" : "text-red-400")
        : "text-slate-500",
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map(({ label, value, subtext, icon: Icon, gradient, shadow, tooltip, valueColor, subtextColor }) => (
        <div key={label} className="glass-card-hover p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider flex items-center">
              {label}
              <MetricTooltip text={tooltip} />
            </span>
            <div className={`w-9 h-9 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center shadow-lg ${shadow}`}>
              <Icon className="w-4 h-4 text-white" />
            </div>
          </div>
          <div className={`text-2xl font-bold mb-1 ${valueColor}`}>{value}</div>
          <div className={`text-xs ${subtextColor ?? "text-slate-500"}`}>{subtext}</div>
        </div>
      ))}
    </div>
  );
}
