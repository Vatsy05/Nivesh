"use client";

import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, AlertCircle, CheckCircle } from "lucide-react";

interface Props {
  onUpload: (file: File) => void;
  uploading: boolean;
  progress: number;
  error: string;
}

export default function UploadZone({ onUpload, uploading, progress, error }: Props) {
  const onDrop = useCallback((accepted: File[], rejected: any[]) => {
    if (rejected.length > 0) return;
    if (accepted.length > 0) onUpload(accepted[0]);
  }, [onUpload]);

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    maxFiles: 1,
    disabled: uploading,
  });

  return (
    <div className="glass-card p-8">
      <div
        {...getRootProps()}
        className={`relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-300
          ${isDragActive && !isDragReject ? "border-indigo-400 bg-indigo-500/10 scale-[1.01]"
            : isDragReject ? "border-red-400 bg-red-500/10"
            : uploading ? "border-slate-700 cursor-not-allowed opacity-60"
            : "border-slate-700 hover:border-indigo-500/40 hover:bg-indigo-500/5"
          }`}
      >
        <input {...getInputProps()} />
        {uploading ? (
          <div className="space-y-4">
            <div className="w-16 h-16 mx-auto rounded-2xl bg-indigo-500/20 flex items-center justify-center">
              <div className="w-8 h-8 border-3 border-indigo-400 border-t-transparent rounded-full animate-spin" />
            </div>
            <p className="text-slate-50 font-medium">Uploading & Parsing...</p>
            <div className="max-w-xs mx-auto">
              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-indigo-500 to-fuchsia-500 rounded-full transition-all duration-500" style={{ width: `${progress}%` }} />
              </div>
              <p className="text-sm text-slate-500 mt-2">{progress}%</p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className={`w-16 h-16 mx-auto rounded-2xl flex items-center justify-center transition-colors ${isDragActive ? "bg-indigo-500/20" : "bg-slate-800/50"}`}>
              {isDragReject ? <AlertCircle className="w-8 h-8 text-red-400" />
                : isDragActive ? <CheckCircle className="w-8 h-8 text-indigo-400" />
                : <Upload className="w-8 h-8 text-slate-500" />}
            </div>
            {isDragReject ? (
              <p className="text-red-400 font-medium">Only PDF files are accepted</p>
            ) : isDragActive ? (
              <p className="text-indigo-400 font-medium">Drop your PDF here...</p>
            ) : (
              <div>
                <p className="text-slate-50 font-medium">Drag & drop your CAMS/CAS statement</p>
                <p className="text-sm text-slate-500 mt-1">or <span className="text-indigo-400 underline underline-offset-2">click to browse</span></p>
                <div className="flex items-center justify-center gap-2 mt-4">
                  <FileText className="w-4 h-4 text-slate-600" />
                  <span className="text-xs text-slate-600">PDF files only</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
      {error && (
        <div className="flex items-center gap-2 mt-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm animate-slide-up">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />{error}
        </div>
      )}
    </div>
  );
}
