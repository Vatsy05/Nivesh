import HoldingsDashboard from "./HoldingsDashboard";

export const metadata = {
  title: "My Portfolio — Nivesh",
  description: "Live mutual fund portfolio with holdings, returns, and growth history",
};

// Auth is enforced by middleware (src/middleware.ts) for all /dashboard/* routes.
// We don't need a server-side auth() call here — it caused the entire page
// (including the Navbar) to hang blank whenever NextAuth/Supabase was slow.
export default function DashboardPage() {
  return <HoldingsDashboard />;
}
