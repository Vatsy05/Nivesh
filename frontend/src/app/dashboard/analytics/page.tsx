"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import {
  TrendingUp, RefreshCw, AlertCircle, LineChart,
  BarChart3, Activity, Calendar, ChevronDown, Zap, CheckCircle,
} from "lucide-react";
import AnalyticsSummaryCards from "@/components/analytics/AnalyticsSummaryCards";
import FundBreakdownTable from "@/components/analytics/FundBreakdownTable";
import PortfolioGrowthChart from "@/components/charts/PortfolioGrowthChart";
import FundXIRRBar from "@/components/charts/FundXIRRBar";
import RollingReturnChart from "@/components/charts/RollingReturnChart";
import P2PReturnPanel from "@/components/charts/P2PReturnPanel";
import AnalyticsSkeleton from "@/components/skeletons/AnalyticsSkeleton";

// ── Types ─────────────────────────────────────────────────────────────────────

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

interface SummaryData {
  total_invested: number;
  total_current_value: number;
  total_gain_loss: number;
  portfolio_xirr_pct: number | null;
  portfolio_cagr_pct: number | null;
  portfolio_absolute_return_pct: number | null;
  funds: FundMetrics[];
  as_of: string;
}

interface GrowthPoint {
  date: string;
  invested_amount: number;
  current_value: number;
}

interface MarketEvent {
  date: string;
  label: string;
  short_label: string;
  type: string;
  description: string;
}

interface RollingData {
  scheme_code: string;
  summary: Record<string, any>;
  series: Record<string, any[]>;
}

// ── Section header ────────────────────────────────────────────────────────────

function SectionHeader({ icon: Icon, title, subtitle }: {
  icon: React.ElementType;
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="flex items-center gap-3 mb-5">
      <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500/20 to-indigo-400/10 border border-indigo-500/20 flex items-center justify-center">
        <Icon className="w-4 h-4 text-indigo-400" />
      </div>
      <div>
        <h2 className="text-base font-semibold text-slate-50">{title}</h2>
        {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
      </div>
    </div>
  );
}

// ── Growth chart fund selector ────────────────────────────────────────────────

/**
 * Filters the portfolio-level growth series to only include data points
 * on or after the fund's first_investment_date, and scales the current_value
 * by the fund's proportion of total portfolio value. This approximates
 * per-fund growth without needing historical NAV at each point.
 */
function buildFundGrowthSeries(
  portfolioSeries: GrowthPoint[],
  fund: FundMetrics,
  totalCurrentValue: number,
): GrowthPoint[] {
  if (!fund.first_investment_date || !portfolioSeries.length) return [];

  const ratio = totalCurrentValue > 0 ? fund.current_value / totalCurrentValue : 0;
  const fundStart = fund.first_investment_date;

  return portfolioSeries
    .filter((p) => p.date >= fundStart)
    .map((p) => ({
      date: p.date,
      invested_amount: Math.round(p.invested_amount * (fund.invested / (portfolioSeries[portfolioSeries.length - 1]?.invested_amount || 1)) * 100) / 100,
      current_value: Math.round(p.current_value * ratio * 100) / 100,
    }));
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [growth, setGrowth] = useState<GrowthPoint[]>([]);
  const [events, setEvents] = useState<MarketEvent[]>([]);
  const [rollingData, setRollingData] = useState<RollingData | null>(null);
  const [rollingLoading, setRollingLoading] = useState(false);
  const [selectedScheme, setSelectedScheme] = useState<string | null>(null);

  // Growth chart: "all" = portfolio-wide, or fund_name string
  const [growthFilter, setGrowthFilter] = useState<string>("all");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [asOf, setAsOf] = useState<string>("");
  const [rematching, setRematching] = useState(false);
  const [rematchResult, setRematchResult] = useState<string>("");

  const handleRematch = async () => {
    setRematching(true);
    setRematchResult("");
    try {
      const res = await fetch("/api/python/analytics/rematch", { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Rematch failed");
      setRematchResult(data.message);
      // Refresh all data after rematching
      await fetchAll(true);
    } catch (err: any) {
      setRematchResult(`Error: ${err.message}`);
    } finally {
      setRematching(false);
    }
  };

  // Fetch summary + growth + events in parallel
  const fetchAll = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    setError("");
    try {
      const [summaryRes, growthRes, eventsRes] = await Promise.all([
        fetch("/api/python/analytics/summary"),
        fetch("/api/python/analytics/growth"),
        fetch("/api/python/analytics/events"),
      ]);

      if (!summaryRes.ok) throw new Error("Failed to load analytics summary");
      const summaryData = await summaryRes.json();
      setSummary(summaryData);
      setAsOf(summaryData.as_of || "");

      if (growthRes.ok) {
        const growthData = await growthRes.json();
        setGrowth(growthData.series || []);
      }

      if (eventsRes.ok) {
        const eventsData = await eventsRes.json();
        setEvents(eventsData.events || []);
      }

      // Auto-select first matched fund for rolling chart
      const firstMatchedFund = summaryData.funds?.find((f: FundMetrics) => f.scheme_code);
      if (firstMatchedFund?.scheme_code) {
        setSelectedScheme((prev) => prev ?? firstMatchedFund.scheme_code);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load analytics");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // Fetch rolling data when selected scheme changes
  const fetchRolling = useCallback(async (scheme: string) => {
    setRollingLoading(true);
    try {
      const res = await fetch(`/api/python/analytics/rolling?scheme_code=${scheme}`);
      if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail || "Failed to load rolling returns");
      }
      const data = await res.json();
      setRollingData(data);
    } catch {
      setRollingData(null);
    } finally {
      setRollingLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedScheme) fetchRolling(selectedScheme);
  }, [selectedScheme, fetchRolling]);

  // Compute the growth series to display
  const displayGrowth = useMemo<GrowthPoint[]>(() => {
    if (growthFilter === "all" || !summary) return growth;
    const fund = summary.funds.find((f) => f.fund_name === growthFilter);
    if (!fund) return growth;
    return buildFundGrowthSeries(growth, fund, summary.total_current_value);
  }, [growth, growthFilter, summary]);

  // Rolling chart subtitle
  const rollingSubtitle = useMemo(() => {
    if (!selectedScheme || !summary) return "Select a fund in the table below";
    const fund = summary.funds.find((f) => f.scheme_code === selectedScheme);
    const name = fund ? fund.fund_name.slice(0, 40) + (fund.fund_name.length > 40 ? "…" : "") : selectedScheme;
    return `${name} · Click any fund row below to switch`;
  }, [selectedScheme, summary]);

  if (loading) return <AnalyticsSkeleton />;

  const noData = !summary || summary.funds.length === 0;
  const matchedFunds = summary?.funds.filter((f) => f.scheme_code) ?? [];

  const selectStyle: React.CSSProperties = {
    padding: "0.375rem 0.75rem",
    borderRadius: "0.5rem",
    background: "rgba(15,23,42,0.7)",
    border: "1px solid rgba(255,255,255,0.1)",
    color: "#cbd5e1",
    fontSize: "0.75rem",
    outline: "none",
    cursor: "pointer",
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between mb-4 animate-fade-in">
        <div>
          <h1 className="text-3xl font-bold text-slate-50 flex items-center gap-3">
            <TrendingUp className="w-8 h-8 text-fuchsia-400" />
            Analytics
          </h1>
          <p className="text-slate-400 mt-2 text-sm">
            Returns &amp; Performance
            {asOf && (
              <span className="ml-2 text-slate-600">
                · as of {new Date(asOf).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRematch}
            disabled={rematching || refreshing}
            title="Re-run AMFI scheme matching for unmatched funds"
            className="btn-secondary flex items-center gap-2 text-sm py-2 border-amber-500/30 text-amber-400 hover:border-amber-500/60"
          >
            <Zap className={`w-4 h-4 ${rematching ? "animate-pulse" : ""}`} />
            {rematching ? "Matching…" : "Re-match Funds"}
          </button>
          <button
            onClick={() => fetchAll(true)}
            disabled={refreshing || rematching}
            className="btn-secondary flex items-center gap-2 text-sm py-2"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Re-match result banner */}
      {rematchResult && (
        <div className={`flex items-center gap-3 p-3 mb-4 rounded-xl text-sm animate-slide-up border ${
          rematchResult.startsWith("Error")
            ? "bg-red-500/10 border-red-500/20 text-red-400"
            : "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
        }`}>
          {rematchResult.startsWith("Error")
            ? <AlertCircle className="w-4 h-4 flex-shrink-0" />
            : <CheckCircle className="w-4 h-4 flex-shrink-0" />}
          {rematchResult}
        </div>
      )}

      {error && (
        <div className="flex items-center gap-3 p-4 mb-6 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm animate-slide-up">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          {error}
        </div>
      )}

      {noData ? (
        /* ── Empty state ──────────────────────────────────────────────── */
        <div className="glass-card p-12 text-center animate-fade-in">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-slate-800/60 flex items-center justify-center mb-4">
            <LineChart className="w-8 h-8 text-slate-600" />
          </div>
          <h3 className="text-lg font-semibold text-slate-400 mb-2">No Portfolio Data</h3>
          <p className="text-sm text-slate-600 max-w-xs mx-auto">
            Upload a CAMS/CAS statement or add transactions manually to see analytics.
          </p>
        </div>
      ) : (
        <>
          {/* ── Summary Cards ────────────────────────────────────────────── */}
          <div className="mb-8 animate-slide-up">
            <AnalyticsSummaryCards data={summary!} />
          </div>

          {/* ── Portfolio Growth Chart ───────────────────────────────────── */}
          <div className="glass-card p-6 mb-6 animate-slide-up">
            <div className="flex items-center justify-between mb-5">
              <SectionHeader
                icon={LineChart}
                title="Portfolio Growth"
                subtitle="Invested amount vs current value over time"
              />
              {/* Fund selector for growth chart */}
              <div className="flex items-center gap-2 ml-auto">
                <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
                <select
                  value={growthFilter}
                  onChange={(e) => setGrowthFilter(e.target.value)}
                  style={selectStyle}
                >
                  <option value="all" style={{ background: "#0f172a" }}>All Funds (Portfolio)</option>
                  {summary!.funds.map((f) => (
                    <option key={f.fund_name} value={f.fund_name} style={{ background: "#0f172a" }}>
                      {f.fund_name.length > 50 ? f.fund_name.slice(0, 50) + "…" : f.fund_name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <PortfolioGrowthChart
              data={displayGrowth}
              events={growthFilter === "all" ? events : []}
            />
            {growthFilter !== "all" && (
              <p className="text-xs text-slate-600 mt-2 px-1">
                ⚠ Per-fund growth is an approximation (current NAV ratio applied over time). Use Rolling Returns for exact historical NAV performance.
              </p>
            )}
          </div>

          {/* ── XIRR + Rolling (2-col) ──────────────────────────────────── */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* Fund XIRR Ranking */}
            <div className="glass-card p-6 animate-slide-up">
              <SectionHeader
                icon={BarChart3}
                title="Fund XIRR Ranking"
                subtitle="Best to worst — sorted by annualised return"
              />
              <FundXIRRBar funds={summary!.funds} />
            </div>

            {/* Rolling Returns */}
            <div className="glass-card p-6 animate-slide-up">
              <SectionHeader
                icon={Activity}
                title="Rolling Returns"
                subtitle={rollingSubtitle}
              />
              {rollingLoading ? (
                <div className="h-56 flex flex-col items-center justify-center gap-3">
                  <div className="w-7 h-7 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                  <p className="text-xs text-slate-600">Fetching NAV history…</p>
                </div>
              ) : rollingData ? (
                <RollingReturnChart
                  series={rollingData.series as any}
                  summary={rollingData.summary as any}
                />
              ) : (
                <div className="h-56 flex items-center justify-center text-slate-600 text-sm">
                  {selectedScheme
                    ? "Could not load NAV history for this fund (unmatched or API unavailable)"
                    : "Select a matched fund to view rolling returns"}
                </div>
              )}
            </div>
          </div>

          {/* ── Point-to-Point Return ────────────────────────────────────── */}
          <div className="glass-card p-6 mb-6 animate-slide-up">
            <SectionHeader
              icon={Calendar}
              title="Point-to-Point Return"
              subtitle="Calculate exact NAV-based return between any two dates"
            />
            {matchedFunds.length > 0 ? (
              <P2PReturnPanel
                funds={matchedFunds.map((f) => ({ scheme_code: f.scheme_code!, fund_name: f.fund_name }))}
              />
            ) : (
              <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 text-sm">
                No funds are matched to AMFI scheme codes yet. Point-to-point return requires historical NAV data, which is only available for matched funds.
              </div>
            )}
          </div>

          {/* ── Fund Breakdown Table ─────────────────────────────────────── */}
          <div className="animate-slide-up">
            <div className="flex items-center gap-3 mb-4">
              <h2 className="text-xl font-semibold text-slate-50 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-indigo-400" />
                Fund Breakdown
              </h2>
              <span className="text-xs text-slate-600">
                Click a row to load its rolling returns →
              </span>
            </div>
            <FundBreakdownTable
              funds={summary!.funds}
              onSelectScheme={(s) => {
                setSelectedScheme(s);
                // Scroll to rolling chart section
                document.getElementById("rolling-section")?.scrollIntoView({ behavior: "smooth" });
              }}
            />
          </div>
        </>
      )}
    </div>
  );
}
