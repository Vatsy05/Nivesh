"use client";

import { useState } from "react";
import { Calendar, TrendingUp, TrendingDown, AlertCircle, RefreshCw, Info } from "lucide-react";

interface FundOption {
  scheme_code: string;
  fund_name: string;
}

interface Props {
  funds: FundOption[];
}

export default function P2PReturnPanel({ funds }: Props) {
  const validFunds = funds.filter((f) => f.scheme_code);
  const [schemeCode, setSchemeCode] = useState(validFunds[0]?.scheme_code ?? "");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [loading, setLoading] = useState(false);
  const [firstLoad, setFirstLoad] = useState(true); // first fetch fetches NAV history
  const [result, setResult] = useState<{ return_pct: number | null; message: string | null } | null>(null);
  const [error, setError] = useState("");

  const handleCompute = async () => {
    if (!schemeCode || !startDate || !endDate) {
      setError("Please select a fund and both dates.");
      return;
    }
    if (startDate >= endDate) {
      setError("Start date must be before end date.");
      return;
    }

    setError("");
    setResult(null);
    setLoading(true);

    try {
      const res = await fetch(
        `/api/python/analytics/p2p?scheme_code=${schemeCode}&start=${startDate}&end=${endDate}`
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Computation failed");
      setResult({ return_pct: data.return_pct, message: data.message });
      setFirstLoad(false);
    } catch (err: any) {
      setError(err.message || "Failed to compute return");
    } finally {
      setLoading(false);
    }
  };

  if (!validFunds.length) {
    return (
      <div className="p-6 text-center text-slate-600 text-sm">
        No matched funds available for point-to-point calculation.
        <p className="text-xs mt-1 text-slate-700">Upload a statement or manually match fund scheme codes.</p>
      </div>
    );
  }

  const ret = result?.return_pct;
  const isPositive = ret !== null && ret !== undefined && ret >= 0;

  const inputStyle: React.CSSProperties = {
    width: "100%",
    padding: "0.5rem 0.75rem",
    borderRadius: "0.5rem",
    background: "rgba(15,23,42,0.6)",
    border: "1px solid rgba(255,255,255,0.1)",
    color: "#e2e8f0",
    fontSize: "0.875rem",
    outline: "none",
    colorScheme: "dark",
  };

  const selectStyle: React.CSSProperties = {
    ...inputStyle,
    cursor: "pointer",
  };

  return (
    <div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-5">
        {/* Fund selector */}
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1.5">Fund</label>
          <select
            value={schemeCode}
            onChange={(e) => { setSchemeCode(e.target.value); setResult(null); setFirstLoad(true); }}
            style={selectStyle}
          >
            {validFunds.map((f) => (
              <option key={f.scheme_code} value={f.scheme_code} style={{ background: "#0f172a" }}>
                {f.fund_name.length > 45 ? f.fund_name.slice(0, 45) + "…" : f.fund_name}
              </option>
            ))}
          </select>
        </div>

        {/* Start date */}
        <div>
          <label className="flex items-center gap-1 text-xs font-medium text-slate-400 mb-1.5">
            <Calendar className="w-3.5 h-3.5" /> Start Date
          </label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => { setStartDate(e.target.value); setResult(null); }}
            max={endDate || new Date().toISOString().split("T")[0]}
            style={inputStyle}
          />
        </div>

        {/* End date */}
        <div>
          <label className="flex items-center gap-1 text-xs font-medium text-slate-400 mb-1.5">
            <Calendar className="w-3.5 h-3.5" /> End Date
          </label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => { setEndDate(e.target.value); setResult(null); }}
            min={startDate}
            max={new Date().toISOString().split("T")[0]}
            style={inputStyle}
          />
        </div>
      </div>

      {/* First-load info hint */}
      {firstLoad && (
        <div className="flex items-start gap-2 p-3 mb-4 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs">
          <Info className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <span>
            The first calculation downloads the fund&apos;s complete NAV history from AMFI — this may take
            10–20 seconds. Subsequent calculations for the same fund will be instant.
          </span>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 p-3 mb-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      <button
        onClick={handleCompute}
        disabled={loading || !schemeCode || !startDate || !endDate}
        className="btn-primary text-sm py-2.5 px-6 flex items-center gap-2 mb-5 disabled:opacity-50"
      >
        {loading ? (
          <>
            <RefreshCw className="w-4 h-4 animate-spin" />
            {firstLoad ? "Fetching NAV history…" : "Computing…"}
          </>
        ) : (
          <><TrendingUp className="w-4 h-4" /> Calculate Return</>
        )}
      </button>

      {/* Result display */}
      {result && (
        <div className={`rounded-2xl p-5 border transition-all animate-slide-up ${
          ret == null
            ? "bg-slate-800/40 border-white/10"
            : isPositive
            ? "bg-emerald-500/10 border-emerald-500/20"
            : "bg-red-500/10 border-red-500/20"
        }`}>
          {ret != null ? (
            <div className="flex items-center gap-4">
              <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${
                isPositive ? "bg-emerald-500/20" : "bg-red-500/20"
              }`}>
                {isPositive
                  ? <TrendingUp className="w-6 h-6 text-emerald-400" />
                  : <TrendingDown className="w-6 h-6 text-red-400" />}
              </div>
              <div>
                <p className="text-xs text-slate-500 mb-0.5">
                  {startDate} → {endDate}
                </p>
                <p className={`text-3xl font-bold ${isPositive ? "text-emerald-400" : "text-red-400"}`}>
                  {isPositive ? "+" : ""}{ret.toFixed(2)}%
                </p>
                <p className="text-xs text-slate-500 mt-0.5">Point-to-Point Return (NAV basis)</p>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-3 text-slate-400 text-sm">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              {result.message || "Return could not be computed for the selected dates."}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
