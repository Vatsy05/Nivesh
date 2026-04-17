"use client";

import { CheckCircle, AlertTriangle, FileText, BarChart3, Building2 } from "lucide-react";

interface Props {
  result: {
    parse_status: string;
    transactions_extracted: number;
    funds_found: string[];
  };
}

const statusMap: Record<string, { icon: any; color: string; bg: string; border: string; label: string }> = {
  success: { icon: CheckCircle, color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20", label: "Successfully Parsed" },
  partial: { icon: AlertTriangle, color: "text-amber-400", bg: "bg-amber-500/10", border: "border-amber-500/20", label: "Partially Parsed" },
  failed: { icon: AlertTriangle, color: "text-red-400", bg: "bg-red-500/10", border: "border-red-500/20", label: "Parsing Failed" },
  pending: { icon: FileText, color: "text-slate-400", bg: "bg-slate-800/50", border: "border-slate-700", label: "Processing..." },
};

export default function ParseSummary({ result }: Props) {
  const config = statusMap[result.parse_status] || statusMap.pending;
  const StatusIcon = config.icon;

  return (
    <div className={`glass-card p-6 border ${config.border} animate-slide-up`}>
      <div className="flex items-center gap-3 mb-6">
        <div className={`w-10 h-10 rounded-xl ${config.bg} flex items-center justify-center`}>
          <StatusIcon className={`w-5 h-5 ${config.color}`} />
        </div>
        <div>
          <h3 className={`font-semibold ${config.color}`}>{config.label}</h3>
          <p className="text-sm text-slate-500">
            {result.parse_status === "success" ? "All transactions extracted" : result.parse_status === "partial" ? "Some transactions may need review" : "Could not extract transactions"}
          </p>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-slate-900/40 rounded-xl p-4 text-center border border-white/5">
          <div className="w-8 h-8 mx-auto rounded-lg bg-gradient-to-br from-indigo-500 to-indigo-400 flex items-center justify-center mb-2">
            <FileText className="w-4 h-4 text-white" />
          </div>
          <div className="text-2xl font-bold text-slate-50">{result.transactions_extracted}</div>
          <div className="text-xs text-slate-500 mt-1">Transactions</div>
        </div>
        <div className="bg-slate-900/40 rounded-xl p-4 text-center border border-white/5">
          <div className="w-8 h-8 mx-auto rounded-lg bg-gradient-to-br from-fuchsia-500 to-fuchsia-400 flex items-center justify-center mb-2">
            <Building2 className="w-4 h-4 text-white" />
          </div>
          <div className="text-2xl font-bold text-slate-50">{result.funds_found.length}</div>
          <div className="text-xs text-slate-500 mt-1">Funds</div>
        </div>
      </div>
    </div>
  );
}
