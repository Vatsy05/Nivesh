"use client";

import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, Calendar } from "lucide-react";

interface Props {
  transactions: any[];
}

interface MonthData {
  key: string;
  year: number;
  month: number;
  count: number;
  amount: number;
}

export default function SIPHeatmap({ transactions }: Props) {
  // Group SIP transactions by fund
  const fundMap = useMemo(() => {
    const map: Record<string, any[]> = {};
    transactions.forEach((t) => {
      if (t.transaction_type === "SIP") {
        if (!map[t.fund_name]) map[t.fund_name] = [];
        map[t.fund_name].push(t);
      }
    });
    return map;
  }, [transactions]);

  const fundNames = Object.keys(fundMap);

  if (fundNames.length === 0) {
    return (
      <div className="glass-card p-8 text-center">
        <Calendar className="w-10 h-10 mx-auto text-slate-700 mb-3" />
        <p className="text-slate-500 text-sm">No SIP transactions found</p>
        <p className="text-slate-600 text-xs mt-1">Upload a statement with SIP transactions to see the heatmap</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {fundNames.map((fname) => (
        <FundHeatmap key={fname} fundName={fname} transactions={fundMap[fname]} />
      ))}
    </div>
  );
}

function FundHeatmap({ fundName, transactions }: { fundName: string; transactions: any[] }) {
  const [expanded, setExpanded] = useState(true);
  const [hoveredCell, setHoveredCell] = useState<MonthData | null>(null);

  // Build month grid data
  const { monthGrid, sipMonths, totalMonths } = useMemo(() => {
    const map: Record<string, { count: number; amount: number }> = {};
    const dates = transactions
      .filter((t) => t.transaction_date)
      .map((t) => new Date(t.transaction_date))
      .sort((a, b) => a.getTime() - b.getTime());

    if (dates.length === 0) return { monthGrid: [], sipMonths: 0, totalMonths: 0 };

    transactions.forEach((t) => {
      if (!t.transaction_date) return;
      const d = new Date(t.transaction_date);
      const key = `${d.getFullYear()}-${d.getMonth()}`;
      if (!map[key]) map[key] = { count: 0, amount: 0 };
      map[key].count += 1;
      map[key].amount += parseFloat(t.amount_inr) || 0;
    });

    const startYear = dates[0].getFullYear();
    const startMonth = dates[0].getMonth();
    const now = new Date();
    const endYear = now.getFullYear();
    const endMonth = now.getMonth();

    const grid: MonthData[] = [];
    let y = startYear;
    let m = startMonth;
    while (y < endYear || (y === endYear && m <= endMonth)) {
      const key = `${y}-${m}`;
      const data = map[key];
      grid.push({
        key,
        year: y,
        month: m,
        count: data?.count || 0,
        amount: data?.amount || 0,
      });
      m++;
      if (m > 11) { m = 0; y++; }
    }

    return {
      monthGrid: grid,
      sipMonths: Object.keys(map).length,
      totalMonths: grid.length,
    };
  }, [transactions]);

  const consistency = totalMonths > 0 ? Math.round((sipMonths / totalMonths) * 100) : 0;

  const monthLabels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  const getCellColor = (count: number) => {
    if (count === 0) return "bg-slate-800/60";
    if (count === 1) return "bg-emerald-800";
    if (count === 2) return "bg-emerald-600";
    if (count === 3) return "bg-emerald-500";
    return "bg-emerald-400";
  };

  // Group months into rows by year for a GitHub-style grid
  const yearGroups = useMemo(() => {
    const groups: Record<number, MonthData[]> = {};
    monthGrid.forEach((m) => {
      if (!groups[m.year]) groups[m.year] = [];
      groups[m.year].push(m);
    });
    return Object.entries(groups).sort(([a], [b]) => parseInt(a) - parseInt(b));
  }, [monthGrid]);

  return (
    <div className="glass-card overflow-hidden">
      <button onClick={() => setExpanded(!expanded)} className="w-full flex items-center justify-between px-6 py-4 hover:bg-white/[0.02] transition-colors">
        <div className="flex items-center gap-3">
          {expanded ? <ChevronDown className="w-4 h-4 text-slate-500" /> : <ChevronRight className="w-4 h-4 text-slate-500" />}
          <div className="text-left">
            <h3 className="text-sm font-semibold text-slate-50 truncate max-w-[400px]">{fundName}</h3>
            <p className="text-xs text-slate-500 mt-0.5">{sipMonths} of {totalMonths} months &middot; {consistency}% consistent</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="w-24 h-2 bg-slate-800 rounded-full overflow-hidden">
            <div className={`h-full rounded-full transition-all duration-700 ${consistency >= 80 ? "bg-emerald-500" : consistency >= 50 ? "bg-amber-500" : "bg-red-500"}`} style={{ width: `${consistency}%` }} />
          </div>
          <span className={`text-xs font-semibold ${consistency >= 80 ? "text-emerald-400" : consistency >= 50 ? "text-amber-400" : "text-red-400"}`}>{consistency}%</span>
        </div>
      </button>

      {expanded && (
        <div className="px-6 pb-6 pt-2">
          <div className="overflow-x-auto">
            <div className="inline-flex flex-col gap-1 min-w-fit">
              {/* Month labels */}
              <div className="flex items-center gap-1 ml-12 mb-1">
                {monthLabels.map((label) => (
                  <div key={label} className="w-7 text-center text-[10px] text-slate-600 select-none">{label}</div>
                ))}
              </div>
              {/* Year rows */}
              {yearGroups.map(([year, months]) => (
                <div key={year} className="flex items-center gap-1">
                  <span className="text-[10px] text-slate-600 w-10 text-right mr-1 select-none">{year}</span>
                  {/* Fill empty months at start of year */}
                  {months[0].month > 0 && Array.from({ length: months[0].month }).map((_, i) => (
                    <div key={`empty-${i}`} className="w-7 h-7" />
                  ))}
                  {months.map((m) => (
                    <div
                      key={m.key}
                      className={`w-7 h-7 rounded-md ${getCellColor(m.count)} heatmap-cell cursor-default relative`}
                      onMouseEnter={() => setHoveredCell(m)}
                      onMouseLeave={() => setHoveredCell(null)}
                    >
                      {hoveredCell?.key === m.key && m.count > 0 && (
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 rounded-lg bg-slate-800 border border-white/10 shadow-xl text-xs whitespace-nowrap z-50 pointer-events-none animate-fade-in">
                          <div className="text-slate-50 font-medium">{monthLabels[m.month]} {m.year}</div>
                          <div className="text-emerald-400">₹{m.amount.toLocaleString("en-IN")} · {m.count} SIP{m.count > 1 ? "s" : ""}</div>
                          <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-px border-4 border-transparent border-t-slate-800" />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-4 mt-4 pt-4 border-t border-white/5">
            <span className="text-xs text-slate-600">Legend:</span>
            <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-sm bg-slate-800/60" /><span className="text-xs text-slate-500">No SIP</span></div>
            <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-sm bg-emerald-800" /><span className="text-xs text-slate-500">1 SIP</span></div>
            <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-sm bg-emerald-600" /><span className="text-xs text-slate-500">2 SIPs</span></div>
            <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-sm bg-emerald-400" /><span className="text-xs text-slate-500">3+ SIPs</span></div>
          </div>
        </div>
      )}
    </div>
  );
}
