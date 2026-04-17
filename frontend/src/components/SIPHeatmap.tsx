"use client";

import { useMemo, useState } from "react";
import CalendarHeatmap from "react-calendar-heatmap";
import "react-calendar-heatmap/dist/styles.css";
import { ChevronDown, ChevronRight, Calendar } from "lucide-react";

interface Props {
  transactions: any[];
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

  // Build month data
  const { monthData, startDate, endDate, sipMonths, totalMonths } = useMemo(() => {
    const map: Record<string, { count: number; amount: number }> = {};
    const dates = transactions
      .filter((t) => t.transaction_date)
      .map((t) => new Date(t.transaction_date))
      .sort((a, b) => a.getTime() - b.getTime());

    if (dates.length === 0) return { monthData: [], startDate: new Date(), endDate: new Date(), sipMonths: 0, totalMonths: 0 };

    transactions.forEach((t) => {
      if (!t.transaction_date) return;
      const d = new Date(t.transaction_date);
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
      if (!map[key]) map[key] = { count: 0, amount: 0 };
      map[key].count += 1;
      map[key].amount += parseFloat(t.amount_inr) || 0;
    });

    const start = new Date(dates[0].getFullYear(), dates[0].getMonth(), 1);
    const end = new Date();
    const heatmapData = Object.entries(map).map(([date, data]) => ({
      date,
      count: data.count,
      amount: data.amount,
    }));

    // Count months range
    let total = 0;
    const cur = new Date(start);
    while (cur <= end) { total++; cur.setMonth(cur.getMonth() + 1); }

    return { monthData: heatmapData, startDate: start, endDate: end, sipMonths: Object.keys(map).length, totalMonths: total };
  }, [transactions]);

  const consistency = totalMonths > 0 ? Math.round((sipMonths / totalMonths) * 100) : 0;

  const getTooltip = (value: any) => {
    if (!value || !value.date) return null;
    const d = new Date(value.date);
    const month = d.toLocaleDateString("en-IN", { month: "short", year: "numeric" });
    return `${month}: ₹${value.amount?.toLocaleString("en-IN") || 0} (${value.count || 0} SIP${(value.count || 0) > 1 ? "s" : ""})`;
  };

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
          <div className="[&_.react-calendar-heatmap]:w-full [&_.react-calendar-heatmap_text]:fill-slate-500 [&_.react-calendar-heatmap_text]:text-[10px] [&_.color-empty]:fill-slate-800 [&_.color-scale-1]:fill-emerald-800 [&_.color-scale-2]:fill-emerald-600 [&_.color-scale-3]:fill-emerald-500 [&_.color-scale-4]:fill-emerald-400">
            <CalendarHeatmap
              startDate={startDate}
              endDate={endDate}
              values={monthData}
              classForValue={(value: any) => {
                if (!value || !value.count) return "color-empty";
                if (value.count >= 4) return "color-scale-4";
                if (value.count >= 3) return "color-scale-3";
                if (value.count >= 2) return "color-scale-2";
                return "color-scale-1";
              }}
              titleForValue={getTooltip}
              showWeekdayLabels
            />
          </div>
          <div className="flex items-center gap-4 mt-4 pt-4 border-t border-white/5">
            <span className="text-xs text-slate-600">Legend:</span>
            <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-sm bg-emerald-500" /><span className="text-xs text-slate-500">SIP recorded</span></div>
            <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-sm bg-slate-800" /><span className="text-xs text-slate-500">No SIP</span></div>
          </div>
        </div>
      )}
    </div>
  );
}
