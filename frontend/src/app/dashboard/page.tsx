import { auth } from "@/lib/auth";
import { redirect } from "next/navigation";
import Link from "next/link";
import { Upload, BarChart3, TrendingUp, Sparkles } from "lucide-react";

export default async function DashboardPage() {
  const session = await auth();
  if (!session) redirect("/auth/login");

  const name = session.user?.name || session.user?.email || "Investor";

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="animate-fade-in">
        <h1 className="text-3xl font-bold text-slate-50 flex items-center gap-3">
          <Sparkles className="w-8 h-8 text-fuchsia-400" />
          Welcome, {name}
        </h1>
        <p className="text-slate-400 mt-2">
          Track your mutual fund portfolio with smart insights
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8 animate-slide-up">
        <Link href="/dashboard/upload" className="glass-card-hover p-8 group">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-indigo-400 flex items-center justify-center mb-4 group-hover:shadow-lg group-hover:shadow-indigo-500/20 transition-shadow">
            <Upload className="w-7 h-7 text-white" />
          </div>
          <h2 className="text-xl font-semibold text-slate-50 mb-2">Upload Statement</h2>
          <p className="text-slate-400 text-sm">
            Upload your CAMS or CAS mutual fund statement PDF to auto-extract all transactions
          </p>
        </Link>

        <Link href="/dashboard/portfolio" className="glass-card-hover p-8 group">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500 to-emerald-400 flex items-center justify-center mb-4 group-hover:shadow-lg group-hover:shadow-emerald-500/20 transition-shadow">
            <BarChart3 className="w-7 h-7 text-white" />
          </div>
          <h2 className="text-xl font-semibold text-slate-50 mb-2">View Portfolio</h2>
          <p className="text-slate-400 text-sm">
            See all your transactions, track SIP consistency, and monitor current units
          </p>
        </Link>
      </div>
    </div>
  );
}
