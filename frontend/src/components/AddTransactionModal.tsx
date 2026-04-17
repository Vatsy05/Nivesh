"use client";

import { useState } from "react";
import { X, Plus, Calendar, DollarSign, Hash, FileText, Building2 } from "lucide-react";

const TXN_TYPES = ["SIP", "lumpsum", "redemption", "switch_in", "switch_out"];

interface Props {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: any) => Promise<void>;
}

export default function AddTransactionModal({ open, onClose, onSubmit }: Props) {
  const [formData, setFormData] = useState({
    fund_name: "", scheme_code: "", folio_number: "", transaction_type: "SIP",
    transaction_date: "", amount_inr: "", units: "", nav_at_transaction: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (!open) return null;

  const set = (k: string, v: string) => setFormData((p) => ({ ...p, [k]: v }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await onSubmit({
        fund_name: formData.fund_name,
        scheme_code: formData.scheme_code || null,
        folio_number: formData.folio_number || null,
        transaction_type: formData.transaction_type,
        transaction_date: formData.transaction_date,
        amount_inr: formData.amount_inr ? parseFloat(formData.amount_inr) : null,
        units: formData.units ? parseFloat(formData.units) : null,
        nav_at_transaction: formData.nav_at_transaction ? parseFloat(formData.nav_at_transaction) : null,
      });
      setFormData({ fund_name: "", scheme_code: "", folio_number: "", transaction_type: "SIP", transaction_date: "", amount_inr: "", units: "", nav_at_transaction: "" });
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to add transaction");
    } finally {
      setLoading(false);
    }
  };

  const fields = [
    { k: "fund_name", l: "Fund Name *", icon: Building2, type: "text", ph: "e.g., HDFC Mid-Cap Opportunities Fund", req: true },
    { k: "folio_number", l: "Folio Number", icon: Hash, type: "text", ph: "e.g., 1234567890" },
    { k: "scheme_code", l: "Scheme Code (AMFI)", icon: FileText, type: "text", ph: "Leave blank for auto-match" },
    { k: "transaction_date", l: "Date *", icon: Calendar, type: "date", req: true },
    { k: "amount_inr", l: "Amount (INR)", icon: DollarSign, type: "number", ph: "0.00", step: "0.01" },
    { k: "units", l: "Units", icon: Hash, type: "number", ph: "0.000000", step: "0.000001" },
    { k: "nav_at_transaction", l: "NAV", icon: DollarSign, type: "number", ph: "0.0000", step: "0.0001" },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative glass-card p-6 max-w-lg w-full max-h-[90vh] overflow-y-auto animate-slide-up">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-slate-50 flex items-center gap-2">
            <Plus className="w-5 h-5 text-indigo-400" />Add Transaction
          </h3>
          <button onClick={onClose} className="w-8 h-8 rounded-lg bg-slate-800/50 flex items-center justify-center hover:bg-slate-700"><X className="w-4 h-4 text-slate-400" /></button>
        </div>
        {error && <div className="p-3 mb-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-2">Transaction Type</label>
            <div className="flex flex-wrap gap-2">
              {TXN_TYPES.map((t) => (
                <button key={t} type="button" onClick={() => set("transaction_type", t)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${formData.transaction_type === t ? "bg-indigo-500/20 text-indigo-400 border border-indigo-500/40" : "bg-slate-800/50 text-slate-500 border border-white/5 hover:border-white/10"}`}>
                  {t.replace("_", " ")}
                </button>
              ))}
            </div>
          </div>
          {fields.map(({ k, l, icon: Icon, type, ph, req, step }) => (
            <div key={k}>
              <label className="block text-sm font-medium text-slate-400 mb-2">{l}</label>
              <div className="relative">
                <Icon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input type={type} value={(formData as any)[k]} onChange={(e) => set(k, e.target.value)}
                  className="input-field pl-10 text-sm" placeholder={ph} required={req} step={step} />
              </div>
            </div>
          ))}
          <div className="flex justify-end gap-3 pt-4">
            <button type="button" onClick={onClose} className="btn-secondary text-sm py-2 px-4">Cancel</button>
            <button type="submit" disabled={loading} className="btn-primary text-sm py-2 px-4 flex items-center gap-2">
              {loading ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Plus className="w-4 h-4" />}
              Add
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
