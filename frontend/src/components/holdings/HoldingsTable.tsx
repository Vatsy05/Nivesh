"use client";

import { useState } from "react";
import { ArrowUpRight, ArrowDownRight, ChevronDown, ChevronUp, Minus } from "lucide-react";

export interface HoldingItem {
  fund_name:        string;
  scheme_code:      string | null;
  folio_number:     string | null;
  current_units:    number;
  invested_amount:  number;
  redeemed_amount:  number;
  avg_buy_nav:      number | null;
  current_nav:      number | null;
  current_value:    number;
  unrealized_gain:  number;
  unrealized_pct:   number;
  realized_gain:    number;
  daily_gain:       number;
  daily_gain_pct:   number;
  is_fully_redeemed: boolean;
  first_purchase:   string | null;
  last_transaction: string | null;
}

interface Props {
  holdings: HoldingItem[];
  loading?: boolean;
}

type SortKey = "current_value" | "invested_amount" | "unrealized_gain" | "unrealized_pct" | "daily_gain";

function fmt(n: number): string {
  if (Math.abs(n) >= 10_000_000) return `₹${(n / 10_000_000).toFixed(2)}Cr`;
  if (Math.abs(n) >= 100_000)    return `₹${(n / 100_000).toFixed(2)}L`;
  return `₹${n.toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

function GainCell({ value, pct }: { value: number; pct?: number }) {
  const zero = Math.abs(value) < 0.5;
  const pos  = value > 0;
  const color = zero ? "text-slate-400" : pos ? "text-emerald-400" : "text-red-400";
  const Icon  = zero ? Minus : pos ? ArrowUpRight : ArrowDownRight;

  return (
    <span className={`flex items-center gap-0.5 ${color} font-medium text-sm`}>
      <Icon className="w-3.5 h-3.5 flex-shrink-0" />
      {pos && !zero ? "+" : ""}{fmt(value)}
      {pct !== undefined && (
        <span className="text-xs opacity-75 ml-0.5">
          ({pct.toFixed(2)}%)
        </span>
      )}
    </span>
  );
}

function SkeletonRow() {
  return (
    <tr className="border-b border-white/5">
      {Array.from({ length: 7 }).map((_, i) => (
        <td key={i} className="px-4 py-4">
          <div className="animate-pulse bg-slate-700/60 rounded h-4 w-full" />
        </td>
      ))}
    </tr>
  );
}

export default function HoldingsTable({ holdings, loading }: Props) {
  const [sortKey, setSortKey]   = useState<SortKey>("current_value");
  const [sortAsc, setSortAsc]   = useState(false);
  const [showRedeemed, setShowRedeemed] = useState(false);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(false); }
  };

  const SortIcon = ({ k }: { k: SortKey }) => (
    <span className="ml-1 opacity-50">
      {sortKey === k ? (sortAsc ? <ChevronUp className="w-3 h-3 inline" /> : <ChevronDown className="w-3 h-3 inline" />) : <ChevronDown className="w-3 h-3 inline" />}
    </span>
  );

  const filtered = (showRedeemed ? holdings : holdings.filter(h => !h.is_fully_redeemed))
    .sort((a, b) => {
      const mul = sortAsc ? 1 : -1;
      return (a[sortKey] - b[sortKey]) * mul;
    });

  const redeemedCount = holdings.filter(h => h.is_fully_redeemed).length;

  const thCls = "px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider text-right cursor-pointer select-none hover:text-slate-200 transition-colors";
  const tdCls = "px-4 py-4 text-right";

  return (
    <div className="glass-card overflow-hidden">
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
        <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
          Holdings
        </h3>
        {redeemedCount > 0 && (
          <button
            onClick={() => setShowRedeemed(!showRedeemed)}
            className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            {showRedeemed ? "Hide" : "Show"} {redeemedCount} redeemed
          </button>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/5">
              <th className="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider text-left">Fund</th>
              <th className={thCls} onClick={() => handleSort("current_value")}>
                Value<SortIcon k="current_value" />
              </th>
              <th className={thCls} onClick={() => handleSort("invested_amount")}>
                Invested<SortIcon k="invested_amount" />
              </th>
              <th className={thCls} onClick={() => handleSort("unrealized_gain")}>
                P&amp;L<SortIcon k="unrealized_gain" />
              </th>
              <th className={thCls} onClick={() => handleSort("unrealized_pct")}>
                Return%<SortIcon k="unrealized_pct" />
              </th>
              <th className={thCls} onClick={() => handleSort("daily_gain")}>
                Today<SortIcon k="daily_gain" />
              </th>
              <th className="px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider text-right">Units</th>
            </tr>
          </thead>
          <tbody>
            {loading && Array.from({ length: 4 }).map((_, i) => <SkeletonRow key={i} />)}

            {!loading && filtered.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center text-slate-500 text-sm">
                  No holdings found. Upload a CAS PDF to get started.
                </td>
              </tr>
            )}

            {!loading && filtered.map((h, i) => (
              <tr
                key={`${h.fund_name}-${h.folio_number}-${i}`}
                className={`border-b border-white/5 hover:bg-white/[0.03] transition-colors
                  ${h.is_fully_redeemed ? "opacity-50" : ""}`}
              >
                {/* Fund Name */}
                <td className="px-4 py-4">
                  <div className="flex flex-col">
                    <span className="text-slate-100 font-medium text-sm leading-tight max-w-[200px] truncate">
                      {h.fund_name}
                    </span>
                    <span className="text-xs text-slate-500 mt-0.5">
                      {h.folio_number ? `Folio: ${h.folio_number}` : h.scheme_code || ""}
                      {h.is_fully_redeemed && <span className="ml-2 text-amber-500">Redeemed</span>}
                    </span>
                    {h.first_purchase && (
                      <span className="text-xs text-slate-600">
                        Since {new Date(h.first_purchase).toLocaleDateString("en-IN", { month: "short", year: "numeric" })}
                      </span>
                    )}
                  </div>
                </td>

                {/* Current Value */}
                <td className={tdCls}>
                  <div className="flex flex-col items-end">
                    <span className="text-slate-100 font-semibold">{fmt(h.current_value)}</span>
                    {h.current_nav && (
                      <span className="text-xs text-slate-500">NAV ₹{h.current_nav.toFixed(2)}</span>
                    )}
                  </div>
                </td>

                {/* Invested */}
                <td className={tdCls}>
                  <span className="text-slate-300">{fmt(h.invested_amount)}</span>
                  {h.avg_buy_nav && (
                    <div className="text-xs text-slate-500">Avg ₹{h.avg_buy_nav.toFixed(2)}</div>
                  )}
                </td>

                {/* P&L */}
                <td className={tdCls}>
                  <GainCell value={h.unrealized_gain} />
                  {h.realized_gain !== 0 && (
                    <div className="text-xs text-slate-500 mt-0.5">
                      Realised: {fmt(h.realized_gain)}
                    </div>
                  )}
                </td>

                {/* Return % */}
                <td className={tdCls}>
                  <GainCell value={h.unrealized_pct} />
                </td>

                {/* Today */}
                <td className={tdCls}>
                  <GainCell value={h.daily_gain} pct={h.daily_gain_pct} />
                </td>

                {/* Units */}
                <td className={tdCls}>
                  <span className="text-slate-400 text-sm tabular-nums">
                    {h.current_units.toLocaleString("en-IN", { maximumFractionDigits: 3 })}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
