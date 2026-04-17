import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Nivesh — Smart Portfolio Tracker",
  description:
    "Smart Mutual Fund Portfolio Tracker for Indian Retail Investors. Upload CAMS/CAS statements, track SIPs, and monitor your portfolio.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} min-h-screen bg-slate-950 text-slate-50`}>
        {children}
      </body>
    </html>
  );
}
