import React, { useState, useCallback } from 'react';
import { UploadCloud, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { useAuth } from '@clerk/clerk-react';

interface UploadDropzoneProps {
  onUploadSuccess: () => void;
  userRole: string;
}

export const UploadDropzone: React.FC<UploadDropzoneProps> = ({ onUploadSuccess, userRole }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const { getToken } = useAuth();

  const handleFileUpload = async (files: FileList | File[]) => {
    if (userRole === 'Viewer') {
      setUploadStatus({ type: 'error', message: 'Viewer role permissions restrict document uploads. Please switch to Admin or Specialist role.' });
      return;
    }
    if (!files || files.length === 0) return;
    const file = files[0];
    setUploading(true);
    setUploadStatus(null);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const token = await getToken();
      const res = await fetch('/api/documents/upload', {
        method: 'POST',
        headers: {
          'X-User-Role': userRole,
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });
      if (!res.ok) {
        let errorMsg = 'Upload failed';
        try {
          const errData = await res.json();
          errorMsg = errData.detail || errData.message || errorMsg;
        } catch {
          // Response body is not JSON — read as plain text
          try { const text = await res.text(); errorMsg = text || errorMsg; } catch { }
        }
        throw new Error(errorMsg);
      }
      const data = await res.json();
      setUploadStatus({ type: 'success', message: `Parsed & Indexed "${data.filename}" (${data.page_count} pages, ${data.chunk_count} chunks)` });
      onUploadSuccess();
    } catch (err: any) {
      setUploadStatus({ type: 'error', message: err.message || 'File upload error' });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="bg-surface-0 border border-border-subtle rounded-xl p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-text-main flex items-center gap-2">
          <UploadCloud className="w-4 h-4 text-accent" />
          Upload New Document
        </h3>
        <div className="flex gap-1.5 flex-wrap">
          {['PDF', 'DOCX', 'XLSX', 'CSV', 'TXT', 'OCR'].map((fmt) => (
            <span key={fmt} className="px-2 py-0.5 text-[10px] font-mono bg-surface-2 text-text-secondary border border-border-subtle rounded">{fmt}</span>
          ))}
        </div>
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => { e.preventDefault(); setIsDragging(false); if (e.dataTransfer.files) handleFileUpload(e.dataTransfer.files); }}
        className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${isDragging ? 'border-accent bg-accent-light' : 'border-border-strong bg-surface-1 hover:border-accent hover:bg-accent-light/50'
          }`}
      >
        <input type="file" accept=".pdf,.docx,.doc,.xlsx,.xls,.csv,.txt,.png,.jpg,.jpeg" className="absolute inset-0 opacity-0 cursor-pointer" onChange={(e) => e.target.files && handleFileUpload(e.target.files)} disabled={uploading} aria-label="Upload document file" />
        {uploading ? (
          <div className="flex flex-col items-center justify-center py-4 space-y-3">
            <Loader2 className="w-8 h-8 text-accent animate-spin" />
            <div className="text-sm font-medium text-accent">Parsing & Indexing...</div>
            <p className="text-xs text-text-muted">Extracting content and building vector indices</p>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center space-y-3 py-2">
            <div className="w-10 h-10 rounded-full bg-accent-light flex items-center justify-center text-accent">
              <UploadCloud className="w-5 h-5" />
            </div>
            <div>
              <p className="text-sm font-medium text-text-main">Click or Drag & Drop files to ingest</p>
              <p className="text-xs text-text-muted mt-1">Supports PDF, Word, Excel, CSV, Text, and Images</p>
            </div>
          </div>
        )}
      </div>

      {uploadStatus && (
        <div className={`mt-4 p-3 rounded-lg border text-xs flex items-center space-x-2 ${uploadStatus.type === 'success' ? 'bg-success-light border-emerald-200 text-success' : 'bg-danger-light border-red-200 text-danger'
          }`}>
          {uploadStatus.type === 'success' ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
          <span>{uploadStatus.message}</span>
        </div>
      )}
    </div>
  );
};
