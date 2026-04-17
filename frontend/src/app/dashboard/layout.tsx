import Navbar from "@/components/Navbar";
import Providers from "@/components/Providers";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Providers>
      <div className="min-h-screen bg-slate-950">
        <Navbar />
        <main>{children}</main>
      </div>
    </Providers>
  );
}
