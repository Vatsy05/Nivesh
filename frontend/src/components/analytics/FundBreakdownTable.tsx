"use client";

import { TrendingUp, TrendingDown, ArrowUpDown } from "lucide-react";
import { useState } from "react";

interface FundMetrics {
  fund_name: string;
  scheme_code: string | null;
  invested: number;
  current_value: number;
  gain_loss: number;
  xirr_pct: number | null;
  cagr_pct: number | null;
  absolute_return_pct: number | null;
  first_investment_date: string | null;
}

interface Props {
  funds: FundMetrics[];
  onSelectScheme?: (schemeCode: string) => void;
}

type SortKey = "fund_name" | "xirr_pct" | "cagr_pct" | "absolute_return_pct" | "current_value" | "gain_loss";

function fmtINR(v: number) {
  if (v >= 1_00_00_000) return `₹${(v / 1_00_00_000).toFixed(1)}Cr`;
  if (v >= 1_00_000) return `₹${(v / 1_00_000).toFixed(1)}L`;
  return `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

function fmtPct(v: number | null, digits = 2) {
  if (v == null) return <span className="text-slate-600">N/A</span>;
  const pos = v >= 0;
  return (
    <span className={pos ? "text-emerald-400" : "text-red-400"}>
      {pos ? "+" : ""}{v.toFixed(digits)}%
    </span>
  );
}

export default function FundBreakdownTable({ funds, onSelectScheme }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("xirr_pct");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(key); setSortDir("desc"); }
  };

  const sorted = [...funds].sort((a, b) => {
    let aV: any = a[sortKey];
    let bV: any = b[sortKey];
    // Push nulls to end
    if (aV == null && bV == null) return 0;
    if (aV == null) return 1;
    if (bV == null) return -1;
    if (typeof aV === "string") aV = aV.toLowerCase();
    if (typeof bV === "string") bV = bV.toLowerCase();
    const cmp = aV < bV ? -1 : aV > bV ? 1 : 0;
    return sortDir === "asc" ? cmp : -cmp;
  });

  const SortBtn = ({ k, label }: { k: SortKey; label: string }) => (
    <button
      onClick={() => toggleSort(k)}
      className={`flex items-center gap-1 cursor-pointer hover:text-slate-300 transition-colors ${sortKey === k ? "text-indigo-400" : ""}`}
    >
      {label}
      <ArrowUpDown className="w-3 h-3 opacity-50" />
    </button>
  );

  if (!funds.length) {
    return (
      <div className="glass-card p-8 text-center text-slate-600 text-sm">
        No fund data to display
      </div>
    );
  }

  return (
    <div className="glass-card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/5">
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                <SortBtn k="fund_name" label="Fund" />
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">
                <SortBtn k="current_value" label="Current Value" />
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Invested
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">
                <SortBtn k="gain_loss" label="Gain / Loss" />
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">
                <SortBtn k="xirr_pct" label="XIRR" />
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">
                <SortBtn k="cagr_pct" label="CAGR" />
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">
                <SortBtn k="absolute_return_pct" label="Abs Return" />
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {sorted.map((fund) => {
              const gainPos = fund.gain_loss >= 0;
              return (
                <tr
                  key={fund.fund_name}
                  className={`hover:bg-white/[0.02] transition-colors ${fund.scheme_code && onSelectScheme ? "cursor-pointer" : ""}`}
                  onClick={() => fund.scheme_code && onSelectScheme?.(fund.scheme_code)}
                >
                  <td className="px-4 py-3">
                    <div>
                      <p className="text-sm text-slate-50 font-medium truncate max-w-[220px]">
                        {fund.fund_name}
                      </p>
                      {fund.first_investment_date && (
                        <p className="text-[10px] text-slate-600 mt-0.5">
                          Since {new Date(fund.first_investment_date).toLocaleDateString("en-IN", { month: "short", year: "numeric" })}
                        </p>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="text-sm text-slate-50 font-medium">{fmtINR(fund.current_value)}</span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="text-sm text-slate-400">{fmtINR(fund.invested)}</span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {gainPos
                        ? <TrendingUp className="w-3.5 h-3.5 text-emerald-500" />
                        : <TrendingDown className="w-3.5 h-3.5 text-red-500" />}
                      <span className={`text-sm font-medium ${gainPos ? "text-emerald-400" : "text-red-400"}`}>
                        {gainPos ? "+" : ""}{fmtINR(fund.gain_loss)}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-semibold">{fmtPct(fund.xirr_pct)}</td>
                  <td className="px-4 py-3 text-right text-sm">{fmtPct(fund.cagr_pct)}</td>
                  <td className="px-4 py-3 text-right text-sm">{fmtPct(fund.absolute_return_pct)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
