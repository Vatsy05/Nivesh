"use client";

import { useState, useMemo } from "react";
import { ArrowUpDown, ArrowUp, ArrowDown, Pencil, Trash2, Check, X, AlertTriangle, Filter } from "lucide-react";

const TYPES = ["All", "SIP", "lumpsum", "redemption", "switch_in", "switch_out"];
const BADGE: Record<string, string> = {
  SIP: "badge-success", lumpsum: "badge-info", redemption: "badge-error",
  switch_in: "badge-warning", switch_out: "badge-warning",
};

interface Props {
  transactions: any[];
  readOnly?: boolean;
  onUpdate?: (id: string, data: any) => Promise<void>;
  onDelete?: (id: string) => void;
}

export default function TransactionTable({ transactions, readOnly = false, onUpdate, onDelete }: Props) {
  const [sortField, setSortField] = useState("transaction_date");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [filterType, setFilterType] = useState("All");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editData, setEditData] = useState<any>({});

  const filtered = useMemo(() => {
    let data = [...transactions];
    if (filterType !== "All") data = data.filter((t) => t.transaction_type === filterType);
    data.sort((a, b) => {
      let aV = a[sortField], bV = b[sortField];
      if (sortField === "transaction_date") { aV = new Date(aV); bV = new Date(bV); }
      else if (sortField === "amount_inr") { aV = parseFloat(aV) || 0; bV = parseFloat(bV) || 0; }
      return sortDir === "asc" ? (aV < bV ? -1 : 1) : (aV > bV ? -1 : 1);
    });
    return data;
  }, [transactions, sortField, sortDir, filterType]);

  const toggleSort = (f: string) => {
    if (sortField === f) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortField(f); setSortDir("desc"); }
  };

  const startEdit = (t: any) => {
    setEditingId(t.id);
    setEditData({
      fund_name: t.fund_name, folio_number: t.folio_number || "", transaction_type: t.transaction_type,
      transaction_date: t.transaction_date, amount_inr: t.amount_inr || "", units: t.units || "",
      nav_at_transaction: t.nav_at_transaction || "",
    });
  };

  const saveEdit = async () => {
    if (onUpdate && editingId) {
      const payload: any = {};
      for (const [k, v] of Object.entries(editData)) {
        if (v !== "" && v !== null) {
          payload[k] = ["amount_inr", "units", "nav_at_transaction"].includes(k) ? parseFloat(v as string) : v;
        }
      }
      await onUpdate(editingId, payload);
    }
    setEditingId(null);
  };

  const fmt = (v: any) => v != null ? new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(v) : "—";
  const fmtNum = (v: any, d = 4) => v != null ? parseFloat(v).toFixed(d) : "—";
  const fmtDate = (s: string) => s ? new Date(s).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "—";

  const SortIcon = ({ field }: { field: string }) => {
    if (sortField !== field) return <ArrowUpDown className="w-3 h-3 opacity-30" />;
    return sortDir === "asc" ? <ArrowUp className="w-3 h-3 text-indigo-400" /> : <ArrowDown className="w-3 h-3 text-indigo-400" />;
  };

  return (
    <div className="glass-card overflow-hidden">
      <div className="px-6 py-4 border-b border-white/5 flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2 text-sm text-slate-500"><Filter className="w-4 h-4" />Filter:</div>
        {TYPES.map((t) => (
          <button key={t} onClick={() => setFilterType(t)}
            className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${filterType === t ? "bg-indigo-500/20 text-indigo-400 border border-indigo-500/40" : "bg-slate-800/30 text-slate-500 border border-white/5 hover:border-white/10"}`}>
            {t === "All" ? "All" : t.replace("_", " ")}
          </button>
        ))}
        <span className="text-xs text-slate-600 ml-auto">{filtered.length} transactions</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/5">
              {[
                { k: "fund_name", l: "Fund Name", s: false },
                { k: "folio_number", l: "Folio", s: false },
                { k: "transaction_type", l: "Type", s: false },
                { k: "transaction_date", l: "Date", s: true },
                { k: "amount_inr", l: "Amount (₹)", s: true },
                { k: "units", l: "Units", s: false },
                { k: "nav_at_transaction", l: "NAV", s: false },
                { k: "current_units", l: "Current Units", s: false },
                { k: "scheme_match_status", l: "Status", s: false },
              ].map((c) => (
                <th key={c.k} onClick={() => c.s && toggleSort(c.k)}
                  className={`px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider ${c.s ? "cursor-pointer hover:text-slate-300 select-none" : ""}`}>
                  <div className="flex items-center gap-1">{c.l}{c.s && <SortIcon field={c.k} />}</div>
                </th>
              ))}
              {!readOnly && <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase">Actions</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {filtered.map((t) => (
              <tr key={t.id} className="hover:bg-white/[0.02] transition-colors group">
                <td className="px-4 py-3">
                  {editingId === t.id ? <input className="input-field text-sm py-1 px-2" value={editData.fund_name} onChange={(e) => setEditData({ ...editData, fund_name: e.target.value })} />
                    : <div className="flex items-center gap-2"><span className="text-sm text-slate-50 font-medium truncate max-w-[200px]">{t.fund_name}</span>
                      {t.scheme_match_status === "unmatched" && <span className="badge-warning text-[10px] flex items-center gap-1"><AlertTriangle className="w-3 h-3" />Needs Review</span>}</div>}
                </td>
                <td className="px-4 py-3"><span className="text-sm text-slate-400">{t.folio_number || "—"}</span></td>
                <td className="px-4 py-3">
                  {editingId === t.id ? <select className="input-field text-sm py-1 px-2" value={editData.transaction_type} onChange={(e) => setEditData({ ...editData, transaction_type: e.target.value })}>
                    {["SIP", "lumpsum", "redemption", "switch_in", "switch_out"].map((tp) => <option key={tp} value={tp}>{tp.replace("_", " ")}</option>)}
                  </select> : <span className={BADGE[t.transaction_type] || "badge-info"}>{(t.transaction_type || "").replace("_", " ")}</span>}
                </td>
                <td className="px-4 py-3">
                  {editingId === t.id ? <input type="date" className="input-field text-sm py-1 px-2" value={editData.transaction_date} onChange={(e) => setEditData({ ...editData, transaction_date: e.target.value })} />
                    : <span className="text-sm text-slate-400">{fmtDate(t.transaction_date)}</span>}
                </td>
                <td className="px-4 py-3">
                  {editingId === t.id ? <input type="number" step="0.01" className="input-field text-sm py-1 px-2" value={editData.amount_inr} onChange={(e) => setEditData({ ...editData, amount_inr: e.target.value })} />
                    : <span className="text-sm text-slate-50 font-medium">{fmt(t.amount_inr)}</span>}
                </td>
                <td className="px-4 py-3"><span className="text-sm text-slate-400">{fmtNum(t.units)}</span></td>
                <td className="px-4 py-3"><span className="text-sm text-slate-500">{fmtNum(t.nav_at_transaction)}</span></td>
                <td className="px-4 py-3"><span className="text-sm text-emerald-400 font-medium">{fmtNum(t.current_units)}</span></td>
                <td className="px-4 py-3">
                  {t.scheme_match_status === "matched" ? <span className="badge-success">Matched</span>
                    : t.scheme_match_status === "manual" ? <span className="badge-info">Manual</span>
                    : <span className="badge-warning">Unmatched</span>}
                </td>
                {!readOnly && (
                  <td className="px-4 py-3 text-right">
                    {editingId === t.id ? (
                      <div className="flex items-center justify-end gap-1">
                        <button onClick={saveEdit} className="w-7 h-7 rounded-lg bg-emerald-500/20 flex items-center justify-center hover:bg-emerald-500/30"><Check className="w-4 h-4 text-emerald-400" /></button>
                        <button onClick={() => setEditingId(null)} className="w-7 h-7 rounded-lg bg-slate-800/50 flex items-center justify-center hover:bg-slate-700"><X className="w-4 h-4 text-slate-400" /></button>
                      </div>
                    ) : (
                      <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button onClick={() => startEdit(t)} className="w-7 h-7 rounded-lg bg-slate-800/50 flex items-center justify-center hover:bg-indigo-500/20" title="Edit"><Pencil className="w-3.5 h-3.5 text-slate-400 hover:text-indigo-400" /></button>
                        <button onClick={() => onDelete?.(t.id)} className="w-7 h-7 rounded-lg bg-slate-800/50 flex items-center justify-center hover:bg-red-500/20" title="Delete"><Trash2 className="w-3.5 h-3.5 text-slate-400 hover:text-red-400" /></button>
                      </div>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && <div className="px-6 py-12 text-center text-slate-600 text-sm">No transactions found</div>}
      </div>
    </div>
  );
}
