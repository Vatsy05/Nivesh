"use client";

import { useState, useEffect, useCallback } from "react";
import TransactionTable from "@/components/TransactionTable";
import AddTransactionModal from "@/components/AddTransactionModal";
import ConfirmDialog from "@/components/ConfirmDialog";
import SIPHeatmap from "@/components/SIPHeatmap";
import { BarChart3, Plus, RefreshCw, Calendar, TrendingUp, Wallet, Activity } from "lucide-react";

export default function PortfolioPage() {
  const [transactions, setTransactions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showAddModal, setShowAddModal] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchPortfolio = useCallback(async () => {
    try {
      const res = await fetch("/api/python/portfolio");
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || data.detail || "Failed to load");
      setTransactions(data.transactions || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { fetchPortfolio(); }, [fetchPortfolio]);

  const handleRefresh = async () => { setRefreshing(true); await fetchPortfolio(); };

  const handleAdd = async (data: any) => {
    const res = await fetch("/api/python/portfolio/manual", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
    });
    if (!res.ok) { const d = await res.json(); throw new Error(d.detail || "Failed"); }
    await fetchPortfolio();
  };

  const handleUpdate = async (id: string, data: any) => {
    await fetch(`/api/python/portfolio/${id}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
    });
    await fetchPortfolio();
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    await fetch(`/api/python/portfolio/${deleteTarget}`, { method: "DELETE" });
    setDeleteTarget(null);
    await fetchPortfolio();
  };

  // Stats
  const totalInvested = transactions.filter((t) => ["SIP", "lumpsum"].includes(t.transaction_type)).reduce((s, t) => s + (parseFloat(t.amount_inr) || 0), 0);
  const totalRedeemed = transactions.filter((t) => t.transaction_type === "redemption").reduce((s, t) => s + (parseFloat(t.amount_inr) || 0), 0);
  const uniqueFunds = [...new Set(transactions.map((t) => t.fund_name))].length;
  const sipCount = transactions.filter((t) => t.transaction_type === "SIP").length;

  const stats = [
    { label: "Total Invested", value: `₹${totalInvested.toLocaleString("en-IN", { minimumFractionDigits: 0 })}`, icon: Wallet, gradient: "from-indigo-500 to-indigo-400" },
    { label: "Total Redeemed", value: `₹${totalRedeemed.toLocaleString("en-IN", { minimumFractionDigits: 0 })}`, icon: TrendingUp, gradient: "from-fuchsia-500 to-fuchsia-400" },
    { label: "Active Funds", value: uniqueFunds, icon: BarChart3, gradient: "from-emerald-500 to-emerald-400" },
    { label: "SIP Transactions", value: sipCount, icon: Activity, gradient: "from-amber-500 to-amber-400" },
  ];

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-20 flex justify-center">
        <div className="text-center">
          <div className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-500 text-sm">Loading portfolio...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-8 animate-fade-in">
        <div>
          <h1 className="text-3xl font-bold text-slate-50 flex items-center gap-3">
            <BarChart3 className="w-8 h-8 text-indigo-400" />My Portfolio
          </h1>
          <p className="text-slate-400 mt-2">{transactions.length} transaction{transactions.length !== 1 ? "s" : ""} across {uniqueFunds} fund{uniqueFunds !== 1 ? "s" : ""}</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={handleRefresh} disabled={refreshing} className="btn-secondary flex items-center gap-2 text-sm py-2">
            <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />Refresh NAV
          </button>
          <button onClick={() => setShowAddModal(true)} className="btn-primary flex items-center gap-2 text-sm py-2">
            <Plus className="w-4 h-4" />Add Transaction
          </button>
        </div>
      </div>

      {error && <div className="p-3 mb-6 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{error}</div>}

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8 animate-slide-up">
        {stats.map(({ label, value, icon: Icon, gradient }) => (
          <div key={label} className="glass-card-hover p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">{label}</span>
              <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${gradient} flex items-center justify-center`}>
                <Icon className="w-4 h-4 text-white" />
              </div>
            </div>
            <div className="text-2xl font-bold text-slate-50">{value}</div>
          </div>
        ))}
      </div>

      {/* Table */}
      <div className="mb-8 animate-slide-up">
        <h2 className="text-xl font-semibold text-slate-50 mb-4">Transactions</h2>
        <TransactionTable transactions={transactions} onUpdate={handleUpdate} onDelete={(id) => setDeleteTarget(id)} />
      </div>

      {/* Heatmap */}
      <div className="animate-slide-up">
        <h2 className="text-xl font-semibold text-slate-50 mb-4 flex items-center gap-2">
          <Calendar className="w-5 h-5 text-emerald-400" />SIP Consistency
        </h2>
        <SIPHeatmap transactions={transactions} />
      </div>

      <AddTransactionModal open={showAddModal} onClose={() => setShowAddModal(false)} onSubmit={handleAdd} />
      <ConfirmDialog open={!!deleteTarget} title="Delete Transaction" message="This action cannot be undone." onConfirm={handleDelete} onCancel={() => setDeleteTarget(null)} />
    </div>
  );
}
