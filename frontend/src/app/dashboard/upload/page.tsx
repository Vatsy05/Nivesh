"use client";

import { useState, useCallback, useRef } from "react";
import { useDropzone } from "react-dropzone";
import ParseSummary from "@/components/ParseSummary";
import TransactionTable from "@/components/TransactionTable";
import {
  FileText, Sparkles, ArrowRight, Lock, Upload,
  AlertCircle, CheckCircle, X, Eye, EyeOff, FileCheck,
} from "lucide-react";
import Link from "next/link";

interface UploadResult {
  document_id: string;
  parse_status: string;
  transactions_extracted: number;
  funds_found: string[];
}

// ── Step 1: Dropzone ─────────────────────────────────────────────────────────
function Dropzone({ onFilePicked }: { onFilePicked: (f: File) => void }) {
  const onDrop = useCallback(
    (accepted: File[]) => { if (accepted[0]) onFilePicked(accepted[0]); },
    [onFilePicked]
  );

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    maxFiles: 1,
  });

  return (
    <div className="glass-card p-8">
      <div
        {...getRootProps()}
        className={`relative border-2 border-dashed rounded-2xl p-14 text-center cursor-pointer transition-all duration-300
          ${isDragActive && !isDragReject
            ? "border-indigo-400 bg-indigo-500/10 scale-[1.01]"
            : isDragReject
            ? "border-red-400 bg-red-500/10"
            : "border-slate-700 hover:border-indigo-500/40 hover:bg-indigo-500/5"
          }`}
      >
        <input {...getInputProps()} />
        <div className="space-y-4">
          <div className={`w-16 h-16 mx-auto rounded-2xl flex items-center justify-center transition-colors ${isDragActive ? "bg-indigo-500/20" : "bg-slate-800/50"}`}>
            {isDragReject
              ? <AlertCircle className="w-8 h-8 text-red-400" />
              : isDragActive
              ? <CheckCircle className="w-8 h-8 text-indigo-400" />
              : <Upload className="w-8 h-8 text-slate-500" />
            }
          </div>
          {isDragReject ? (
            <p className="text-red-400 font-medium">Only PDF files are accepted</p>
          ) : isDragActive ? (
            <p className="text-indigo-400 font-medium">Drop your PDF here…</p>
          ) : (
            <div>
              <p className="text-slate-50 font-medium">Drag & drop your CAMS / CAS statement</p>
              <p className="text-sm text-slate-500 mt-1">
                or <span className="text-indigo-400 underline underline-offset-2">click to browse</span>
              </p>
              <div className="flex items-center justify-center gap-2 mt-4">
                <FileText className="w-4 h-4 text-slate-600" />
                <span className="text-xs text-slate-600">PDF files only · password protected PDFs supported</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Step 2: Password + Confirm card ──────────────────────────────────────────
function PasswordStep({
  file,
  onConfirm,
  onCancel,
  uploading,
  progress,
  error,
}: {
  file: File;
  onConfirm: (password: string) => void;
  onCancel: () => void;
  uploading: boolean;
  progress: number;
  error: string;
}) {
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onConfirm(password);
  };

  const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);

  return (
    <div className="glass-card p-8 animate-slide-up">
      {/* File selected banner */}
      <div className="flex items-center gap-3 mb-6 p-4 rounded-xl bg-indigo-500/10 border border-indigo-500/20">
        <div className="w-10 h-10 rounded-xl bg-indigo-500/20 flex items-center justify-center flex-shrink-0">
          <FileCheck className="w-5 h-5 text-indigo-400" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-slate-50 font-medium truncate">{file.name}</p>
          <p className="text-xs text-slate-500 mt-0.5">{fileSizeMB} MB · PDF</p>
        </div>
        {!uploading && (
          <button
            onClick={onCancel}
            className="p-1.5 rounded-lg hover:bg-slate-700 text-slate-500 hover:text-slate-300 transition"
            title="Remove file"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Password field */}
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label
            htmlFor="pdf-password"
            className="block text-sm font-medium text-slate-300 mb-1.5 flex items-center gap-2"
          >
            <Lock className="w-4 h-4 text-indigo-400" />
            PDF Password
            <span className="text-slate-500 font-normal">(leave blank if none)</span>
          </label>
          <div className="relative">
            <input
              ref={inputRef}
              id="pdf-password"
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter PDF password…"
              className="w-full bg-slate-800/60 border border-slate-700 rounded-xl px-4 py-3 pr-11 text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
              autoComplete="off"
              spellCheck={false}
              disabled={uploading}
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition"
              tabIndex={-1}
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          <p className="text-xs text-slate-500 mt-1.5">
            Common passwords: your PAN number, email address, or date of birth (DDMMYYYY).
          </p>
        </div>

        {/* Progress bar */}
        {uploading && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>
                {progress < 90
                  ? "Uploading…"
                  : progress < 100
                  ? "Parsing & matching funds… (this can take 15–30 s)"
                  : "Done!"}
              </span>
              <span>{progress}%</span>
            </div>
            <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-indigo-500 to-fuchsia-500 rounded-full transition-all duration-1000"
                style={{ width: `${progress}%` }}
              />
            </div>
            {progress >= 90 && progress < 100 && (
              <p className="text-xs text-slate-600">
                Matching fund names via MFAPI — please don&apos;t close this tab.
              </p>
            )}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {error}
            {error.toLowerCase().includes("password") && (
              <span className="ml-1 text-slate-400">— try a different password</span>
            )}
          </div>
        )}

        {/* Action buttons */}
        <div className="flex gap-3 pt-1">
          <button
            type="button"
            onClick={onCancel}
            disabled={uploading}
            className="flex-1 py-3 rounded-xl border border-slate-700 text-slate-400 hover:text-slate-200 hover:border-slate-600 transition text-sm font-medium disabled:opacity-40"
          >
            Choose different file
          </button>
          <button
            type="submit"
            disabled={uploading}
            className="flex-1 py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-fuchsia-600 hover:from-indigo-500 hover:to-fuchsia-500 text-white font-semibold transition text-sm disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {uploading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                Parsing…
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Parse Statement
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function UploadPage() {
  const [step, setStep] = useState<"drop" | "password" | "done">("drop");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");

  const handleFilePicked = (file: File) => {
    setSelectedFile(file);
    setError("");
    setStep("password");
  };

  const handleCancel = () => {
    setSelectedFile(null);
    setUploadResult(null);
    setTransactions([]);
    setError("");
    setStep("drop");
  };

  const handleConfirm = async (password: string) => {
    if (!selectedFile) return;
    setError("");
    setUploading(true);
    setProgress(0);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      if (password) formData.append("password", password);

      const response = await new Promise<UploadResult>((resolve, reject) => {
        const xhr = new XMLHttpRequest();

        // Add 3-minute timeout — must exceed the proxy's 180 s upload limit
        xhr.timeout = 200_000;

        // ── Phase 1: upload progress (0 → 90%) ───────────────────────────
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) {
            setProgress(Math.round((e.loaded / e.total) * 90));
          }
        };

        // ── Phase 2: simulated parse progress (90 → 99%) ─────────────────
        // Fires once the file bytes have reached the server. The backend
        // then spends 10-30 s parsing & matching funds — we tick 1% every
        // 2 s so the bar clearly moves instead of freezing at 90%.
        xhr.upload.onloadend = () => {
          let fake = 90;
          const ticker = setInterval(() => {
            fake = Math.min(fake + 1, 99);
            setProgress(fake);
            if (fake >= 99) clearInterval(ticker);
          }, 2_000);
          // Store on xhr so onload can clear it
          (xhr as any)._ticker = ticker;
        };

        xhr.onload = () => {
          if ((xhr as any)._ticker) clearInterval((xhr as any)._ticker);
          setProgress(100);
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(JSON.parse(xhr.responseText));
          } else {
            try { reject(JSON.parse(xhr.responseText)); }
            catch { reject({ error: "Upload failed" }); }
          }
        };

        xhr.onerror = () => {
          if ((xhr as any)._ticker) clearInterval((xhr as any)._ticker);
          reject({ error: "Network error" });
        };

        xhr.ontimeout = () => {
          if ((xhr as any)._ticker) clearInterval((xhr as any)._ticker);
          reject({ error: "PDF parsing timed out — this usually means the password is incorrect. Try leaving the password blank, or check that you entered it correctly." });
        };

        xhr.open("POST", "/api/python/upload");
        xhr.send(formData);
      });

      setUploadResult(response);

      if (response.parse_status === "failed") {
        // Check if it's a password issue
        setError("Could not extract transactions. If the PDF is password protected, please check your password and try again.");
      } else {
        const portfolioRes = await fetch("/api/python/portfolio");
        const portfolioData = await portfolioRes.json();
        setTransactions(portfolioData.transactions || []);
        setStep("done");
      }
    } catch (err: any) {
      // A 504 from the proxy means the proxy timed out, but the backend may
      // have already finished writing to the database. Check if data was saved
      // before showing an error — if it was, redirect to the portfolio.
      const msg = err?.detail || err?.error || "";
      const is504 = msg.toLowerCase().includes("timed out") || msg.toLowerCase().includes("timeout");

      if (is504) {
        try {
          const checkRes = await fetch("/api/python/portfolio");
          const checkData = await checkRes.json();
          if (checkData.transactions && checkData.transactions.length > 0) {
            // Backend succeeded — data is in the DB. Navigate to portfolio.
            window.location.href = "/dashboard/portfolio";
            return;
          }
        } catch {
          // Ignore — fall through to error display
        }
      }

      setError(msg || "Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8 animate-fade-in">
        <h1 className="text-3xl font-bold text-slate-50 flex items-center gap-3">
          <FileText className="w-8 h-8 text-indigo-400" />
          Upload Statement
        </h1>
        <p className="text-slate-400 mt-2 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-fuchsia-400" />
          Upload your CAMS or KFintech CAS PDF to auto-extract all transactions
        </p>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-2 mb-6 text-xs text-slate-500">
        <span className={step === "drop" ? "text-indigo-400 font-semibold" : "text-slate-600"}>
          1. Select PDF
        </span>
        <div className="flex-1 h-px bg-slate-800" />
        <span className={step === "password" ? "text-indigo-400 font-semibold" : "text-slate-600"}>
          2. Unlock & Parse
        </span>
        <div className="flex-1 h-px bg-slate-800" />
        <span className={step === "done" ? "text-indigo-400 font-semibold" : "text-slate-600"}>
          3. Review Transactions
        </span>
      </div>

      {/* Step 1: Dropzone */}
      {step === "drop" && (
        <Dropzone onFilePicked={handleFilePicked} />
      )}

      {/* Step 2: Password + parse */}
      {(step === "password" || (step === "done" && uploadResult?.parse_status === "failed")) && selectedFile && (
        <PasswordStep
          file={selectedFile}
          onConfirm={handleConfirm}
          onCancel={handleCancel}
          uploading={uploading}
          progress={progress}
          error={error}
        />
      )}

      {/* Step 3: Results */}
      {step === "done" && uploadResult && (
        <div className="space-y-8 animate-slide-up">
          <ParseSummary result={uploadResult} />

          {transactions.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-slate-50">
                  Extracted Transactions
                </h2>
                <Link
                  href="/dashboard/portfolio"
                  className="btn-primary text-sm py-2 flex items-center gap-2"
                >
                  Go to Portfolio <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
              <TransactionTable transactions={transactions} readOnly />
            </div>
          )}

          <button
            onClick={handleCancel}
            className="text-sm text-slate-500 hover:text-slate-300 underline underline-offset-2 transition"
          >
            Upload another statement
          </button>
        </div>
      )}
    </div>
  );
}
