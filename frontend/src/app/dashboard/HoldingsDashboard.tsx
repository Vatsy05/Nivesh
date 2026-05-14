"use client";

import { useState, useEffect, useCallback } from "react";
import { RefreshCw, Upload, TrendingUp, Zap, AlertTriangle } from "lucide-react";
import Link from "next/link";

import HoldingsSummaryBar from "@/components/holdings/HoldingsSummaryBar";
import AllocationPieChart from "@/components/holdings/AllocationPieChart";
import HoldingsTable, { HoldingItem } from "@/components/holdings/HoldingsTable";
import PortfolioHistoryChart from "@/components/holdings/PortfolioHistoryChart";

interface SummaryData {
  total_value:     number;
  total_invested:  number;
  total_pnl:       number;
  daily_gain:      number;
  daily_gain_pct:  number;
  xirr_pct:        number | null;
  abs_return_pct:  number | null;
  num_funds:       number;
}

interface SnapshotPoint {
  date:            string;
  invested_amount: number;
  portfolio_value: number;
  daily_pnl:       number;
  total_pnl:       number;
}

export default function HoldingsDashboard() {
  const [summary, setSummary]       = useState<SummaryData | null>(null);
  const [holdings, setHoldings]     = useState<HoldingItem[]>([]);
  const [history, setHistory]       = useState<SnapshotPoint[]>([]);
  const [loadingSummary, setLoadingSummary] = useState(true);
  const [loadingHoldings, setLoadingHoldings] = useState(true);
  const [loadingHistory, setLoadingHistory]   = useState(false);
  const [rebuilding, setRebuilding] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError]           = useState("");
  const [noData, setNoData]         = useState(false);

  // Fetch summary + holdings in parallel (30 s timeout — Supabase via PgBouncer
  // can be slow on the first request after an upload or a cold start).
  const fetchDashboard = useCallback(async () => {
    setRefreshing(true);
    setError("");

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30_000);

    try {
      const [sumRes, holdRes] = await Promise.all([
        fetch("/api/python/holdings/summary", { signal: controller.signal }),
        fetch("/api/python/holdings", { signal: controller.signal }),
      ]);

      if (!sumRes.ok || !holdRes.ok) {
        if (sumRes.status === 404 || holdRes.status === 404) {
          setNoData(true);
          return;
        }
        throw new Error("Failed to load portfolio data");
      }

      const [sumData, holdData] = await Promise.all([
        sumRes.json(),
        holdRes.json(),
      ]);

      setSummary(sumData);
      setHoldings(holdData.holdings || []);

      if (!sumData.total_invested && !(holdData.holdings?.length)) {
        setNoData(true);
      } else {
        setNoData(false);
      }
    } catch (e: any) {
      const isTimeout = e.name === "AbortError";
      const msg = isTimeout
        ? "Dashboard load timed out — click Retry to try again."
        : (e.message || "Failed to load dashboard");
      setError(msg);
      // Only show the empty state when we have no data at all.
      // If holdings already loaded (e.g. this is a refresh), keep them visible.
      setNoData((prev) => prev || isTimeout);
    } finally {
      clearTimeout(timeoutId);
      setLoadingSummary(false);
      setLoadingHoldings(false);
      setRefreshing(false);
    }
  }, []);

  // Fetch history separately (slower — may trigger NAV fetch)
  const fetchHistory = useCallback(async (rebuild = false) => {
    if (rebuild) setRebuilding(true);
    else setLoadingHistory(true);

    try {
      const url = rebuild
        ? "/api/python/holdings/rebuild"
        : "/api/python/holdings/history";
      const method = rebuild ? "POST" : "GET";
      const res = await fetch(url, { method });
      if (!res.ok) return;
      const data = await res.json();
      setHistory(data.history || []);
    } catch (e) {
      console.error("History fetch failed:", e);
    } finally {
      setLoadingHistory(false);
      setRebuilding(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
    fetchHistory();
  }, [fetchDashboard, fetchHistory]);

  // Empty state (no data or backend unreachable)
  if (!loadingSummary && !loadingHoldings && noData) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 animate-fade-in">
        <div className="flex flex-col items-center justify-center text-center glass-card p-16 max-w-lg mx-auto">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-fuchsia-500/20 border border-indigo-500/30 flex items-center justify-center mb-6">
            <TrendingUp className="w-8 h-8 text-indigo-400" />
          </div>
          <h2 className="text-2xl font-bold text-slate-50 mb-3">No Portfolio Yet</h2>
          {error ? (
            <div className="flex items-center gap-2 mb-4 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 text-sm text-left">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          ) : (
            <p className="text-slate-400 mb-8 leading-relaxed">
              Upload your CAMS or CAS Consolidated Account Statement to see your full portfolio with live valuations, returns, and growth history.
            </p>
          )}
          <div className="flex flex-col gap-3 w-full max-w-xs mt-4">
            <Link href="/dashboard/upload" className="btn-primary flex items-center justify-center gap-2">
              <Upload className="w-4 h-4" />
              Upload Statement
            </Link>
            {error && (
              <button
                onClick={() => { fetchDashboard(); fetchHistory(); }}
                className="btn-secondary flex items-center justify-center gap-2 text-sm"
              >
                <RefreshCw className="w-4 h-4" />
                Retry
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-6 animate-fade-in">
        <div>
          <h1 className="text-2xl font-bold text-slate-50">My Portfolio</h1>
          <p className="text-slate-500 text-sm mt-0.5">
            Live valuations · {new Date().toLocaleDateString("en-IN", {
              weekday: "long", day: "numeric", month: "long", year: "numeric",
            })}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/dashboard/upload"
            className="btn-secondary flex items-center gap-2 text-sm py-2"
          >
            <Upload className="w-4 h-4" />
            Upload
          </Link>
          <Link
            href="/dashboard/analytics"
            className="btn-secondary flex items-center gap-2 text-sm py-2 text-fuchsia-400 border-fuchsia-500/30 hover:border-fuchsia-500/50"
          >
            <Zap className="w-4 h-4" />
            Analytics
          </Link>
          <button
            onClick={() => { fetchDashboard(); fetchHistory(); }}
            disabled={refreshing}
            className="btn-secondary flex items-center gap-2 text-sm py-2"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* ── Summary Bar ─────────────────────────────────────────────────── */}
      <HoldingsSummaryBar data={summary} loading={loadingSummary} />

      {/* ── Growth Chart + Allocation ──────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        <div className="lg:col-span-2">
          <PortfolioHistoryChart
            data={history}
            loading={loadingHistory || rebuilding}
            onRebuild={() => fetchHistory(true)}
          />
        </div>
        <div>
          <AllocationPieChart holdings={holdings} loading={loadingHoldings} />
        </div>
      </div>

      {/* ── Holdings Table ───────────────────────────────────────────────── */}
      <div className="animate-slide-up">
        <HoldingsTable holdings={holdings} loading={loadingHoldings} />
      </div>

      {/* ── Footer links ────────────────────────────────────────────────── */}
      <div className="flex items-center justify-center gap-6 mt-6 text-xs text-slate-600">
        <Link href="/dashboard/upload" className="hover:text-slate-400 transition-colors">
          Upload New Statement
        </Link>
        <span>·</span>
        <Link href="/dashboard/portfolio" className="hover:text-slate-400 transition-colors">
          Transaction History
        </Link>
        <span>·</span>
        <Link href="/dashboard/analytics" className="hover:text-slate-400 transition-colors">
          Deep Analytics
        </Link>
      </div>
    </div>
  );
}
