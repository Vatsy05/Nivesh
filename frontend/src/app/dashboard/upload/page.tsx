"use client";

import { useState } from "react";
import UploadZone from "@/components/UploadZone";
import ParseSummary from "@/components/ParseSummary";
import TransactionTable from "@/components/TransactionTable";
import { FileText, Sparkles, ArrowRight } from "lucide-react";
import Link from "next/link";

interface UploadResult {
  document_id: string;
  parse_status: string;
  transactions_extracted: number;
  funds_found: string[];
}

export default function UploadPage() {
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");

  const handleUpload = async (file: File) => {
    setError("");
    setUploading(true);
    setProgress(0);
    setUploadResult(null);
    setTransactions([]);

    try {
      const formData = new FormData();
      formData.append("file", file);

      // Upload via Next.js proxy → FastAPI
      const xhr = new XMLHttpRequest();
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) setProgress(Math.round((e.loaded / e.total) * 100));
      };

      const response = await new Promise<any>((resolve, reject) => {
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(JSON.parse(xhr.responseText));
          } else {
            try { reject(JSON.parse(xhr.responseText)); } catch { reject({ error: "Upload failed" }); }
          }
        };
        xhr.onerror = () => reject({ error: "Network error" });
        xhr.open("POST", "/api/python/upload");
        xhr.send(formData);
      });

      setUploadResult(response);

      // Fetch portfolio to show transactions
      const portfolioRes = await fetch("/api/python/portfolio");
      const portfolioData = await portfolioRes.json();
      setTransactions(portfolioData.transactions || []);
    } catch (err: any) {
      setError(err?.detail || err?.error || "Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8 animate-fade-in">
        <h1 className="text-3xl font-bold text-slate-50 flex items-center gap-3">
          <FileText className="w-8 h-8 text-indigo-400" />
          Upload Statement
        </h1>
        <p className="text-slate-400 mt-2 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-fuchsia-400" />
          Upload your CAMS or CAS mutual fund statement to auto-extract all transactions
        </p>
      </div>

      <div className="animate-slide-up">
        <UploadZone onUpload={handleUpload} uploading={uploading} progress={progress} error={error} />
      </div>

      {uploadResult && (
        <div className="mt-8 animate-slide-up">
          <ParseSummary result={uploadResult} />
        </div>
      )}

      {transactions.length > 0 && (
        <div className="mt-8 animate-slide-up">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-slate-50">Extracted Transactions</h2>
            <Link href="/dashboard/portfolio" className="btn-primary text-sm py-2 flex items-center gap-2">
              Go to Portfolio <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
          <TransactionTable transactions={transactions} readOnly />
        </div>
      )}
    </div>
  );
}
