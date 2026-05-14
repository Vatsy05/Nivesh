"use client";

export default function AnalyticsSkeleton() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-pulse">
      {/* Header */}
      <div className="h-9 w-64 bg-slate-800 rounded-xl mb-2" />
      <div className="h-4 w-48 bg-slate-800/60 rounded-lg mb-8" />

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="glass-card p-5 space-y-3">
            <div className="flex items-center justify-between">
              <div className="h-3 w-24 bg-slate-800 rounded" />
              <div className="w-8 h-8 rounded-lg bg-slate-800" />
            </div>
            <div className="h-7 w-32 bg-slate-800 rounded-lg" />
            <div className="h-3 w-20 bg-slate-800/60 rounded" />
          </div>
        ))}
      </div>

      {/* Growth chart */}
      <div className="glass-card p-6 mb-6">
        <div className="h-5 w-48 bg-slate-800 rounded-lg mb-6" />
        <div className="h-64 bg-slate-800/40 rounded-xl" />
      </div>

      {/* Two-column charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="glass-card p-6">
          <div className="h-5 w-40 bg-slate-800 rounded-lg mb-6" />
          <div className="h-56 bg-slate-800/40 rounded-xl" />
        </div>
        <div className="glass-card p-6">
          <div className="h-5 w-40 bg-slate-800 rounded-lg mb-6" />
          <div className="h-56 bg-slate-800/40 rounded-xl" />
        </div>
      </div>
    </div>
  );
}
