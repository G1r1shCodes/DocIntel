import React, { useState } from 'react';
import { UploadCloud, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';

interface UploadDropzoneProps {
  onUploadSuccess: () => void;
  userRole: string;
}

export const UploadDropzone: React.FC<UploadDropzoneProps> = ({ onUploadSuccess, userRole }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const handleFileUpload = async (files: FileList | File[]) => {
    if (userRole === 'Viewer') {
      setUploadStatus({
        type: 'error',
        message: 'Viewer role permissions restrict document uploads. Please switch to Admin or Specialist role.'
      });
      return;
    }

    if (!files || files.length === 0) return;
    const file = files[0];

    setUploading(true);
    setUploadStatus(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('http://localhost:8000/api/documents/upload', {
        method: 'POST',
        headers: {
          'X-User-Role': userRole
        },
        body: formData
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Upload failed');
      }

      const data = await res.json();
      setUploadStatus({
        type: 'success',
        message: `Parsed & Indexed "${data.filename}" (${data.page_count} pages, ${data.chunk_count} adaptive chunks)`
      });
      onUploadSuccess();
    } catch (err: any) {
      setUploadStatus({
        type: 'error',
        message: err.message || 'File upload error'
      });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
            <UploadCloud className="w-5 h-5 text-cyan-400" />
            Multi-Format Document Upload Pipeline
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Native parsing + Tesseract OCR fallback for PDF, DOCX, XLSX, CSV, TXT, and Images.
          </p>
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {['PDF', 'DOCX', 'XLSX', 'CSV', 'TXT', 'OCR'].map((fmt) => (
            <span key={fmt} className="px-2 py-0.5 text-[10px] font-mono bg-slate-800 text-cyan-400 border border-slate-700 rounded">
              {fmt}
            </span>
          ))}
        </div>
      </div>

      {/* Drag and Drop Zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          if (e.dataTransfer.files) handleFileUpload(e.dataTransfer.files);
        }}
        className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${
          isDragging
            ? 'border-cyan-400 bg-cyan-500/10 scale-[1.01]'
            : 'border-slate-700 bg-slate-950/40 hover:border-slate-600 hover:bg-slate-950/70'
        }`}
      >
        <input
          type="file"
          accept=".pdf,.docx,.doc,.xlsx,.xls,.csv,.txt,.png,.jpg,.jpeg"
          className="absolute inset-0 opacity-0 cursor-pointer"
          onChange={(e) => e.target.files && handleFileUpload(e.target.files)}
          disabled={uploading}
        />

        {uploading ? (
          <div className="flex flex-col items-center justify-center py-4 space-y-3">
            <Loader2 className="w-10 h-10 text-cyan-400 animate-spin" />
            <div className="text-sm font-semibold text-cyan-300">Parsing & Adaptive Chunking...</div>
            <p className="text-xs text-slate-500">Extracting tables, headings, and building vector/BM25 indices</p>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center space-y-3 py-2">
            <div className="w-12 h-12 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-cyan-400">
              <UploadCloud className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-200">
                Click or Drag & Drop enterprise files to ingest
              </p>
              <p className="text-xs text-slate-400 mt-1">
                Supports PDF, Word (.docx), Excel (.xlsx), CSV, Text, and Scanned Images
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Upload Feedback Banner */}
      {uploadStatus && (
        <div
          className={`mt-4 p-3 rounded-lg border text-xs flex items-center space-x-2 ${
            uploadStatus.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
              : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
          }`}
        >
          {uploadStatus.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 shrink-0" />
          )}
          <span>{uploadStatus.message}</span>
        </div>
      )}
    </div>
  );
};
