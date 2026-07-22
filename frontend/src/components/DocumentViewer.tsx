import React, { useState } from 'react';
import { FileText, ChevronLeft, ChevronRight, ZoomIn, ZoomOut } from 'lucide-react';

interface CitationHighlight {
  page_number: number;
  filename: string;
  heading?: string;
  text_snippet: string;
  bbox?: {
    x0: number;
    y0: number;
    x1: number;
    y1: number;
  };
}

interface DocumentViewerProps {
  filename?: string;
  activeCitation?: CitationHighlight | null;
  documentUrl?: string;
}

export const DocumentViewer: React.FC<DocumentViewerProps> = ({
  filename = 'Transformer_Warranty_Manual.pdf',
  activeCitation = null
}) => {
  const [currentPage, setCurrentPage] = useState<number>(activeCitation?.page_number || 1);
  const [zoom, setZoom] = useState<number>(100);

  React.useEffect(() => {
    if (activeCitation?.page_number) {
      setCurrentPage(activeCitation.page_number);
    }
  }, [activeCitation]);

  const targetFilename = activeCitation?.filename || filename;
  const isPdf = targetFilename.toLowerCase().endsWith('.pdf');

  return (
    <div className="flex flex-col h-full bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
      {/* Top Header Bar */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-950 border-b border-slate-800 text-slate-200">
        <div className="flex items-center space-x-2 truncate">
          <FileText className="w-5 h-5 text-cyan-400 shrink-0" />
          <span className="font-semibold text-sm truncate">{targetFilename}</span>
          <span className="px-2 py-0.5 text-xs font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 rounded">
            {isPdf ? 'PDF Native' : 'Extracted Text'}
          </span>
        </div>

        {/* Page & Zoom Controls */}
        <div className="flex items-center space-x-3 text-xs">
          <div className="flex items-center space-x-1 bg-slate-900 px-2 py-1 rounded border border-slate-800">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              className="p-1 hover:text-cyan-400 transition"
              title="Previous Page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-mono px-2">Page {currentPage}</span>
            <button
              onClick={() => setCurrentPage((p) => p + 1)}
              className="p-1 hover:text-cyan-400 transition"
              title="Next Page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center space-x-1 bg-slate-900 px-2 py-1 rounded border border-slate-800">
            <button onClick={() => setZoom((z) => Math.max(50, z - 10))} className="p-1 hover:text-cyan-400">
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="font-mono w-10 text-center">{zoom}%</span>
            <button onClick={() => setZoom((z) => Math.min(200, z + 10))} className="p-1 hover:text-cyan-400">
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Active Citation Header Banner */}
      {activeCitation && (
        <div className="px-4 py-2.5 bg-gradient-to-r from-amber-500/15 to-cyan-500/15 border-b border-amber-500/30 flex items-center justify-between text-xs text-amber-300">
          <div className="flex items-center space-x-2 truncate">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
            <span className="font-semibold">Citation Highlight Active:</span>
            <span className="truncate text-slate-200">{activeCitation.heading || 'Section Context'}</span>
          </div>
          <span className="font-mono bg-amber-500/20 px-2 py-0.5 rounded text-amber-200 shrink-0">
            Target Page {activeCitation.page_number}
          </span>
        </div>
      )}

      {/* Document View Canvas Area */}
      <div className="relative flex-1 overflow-auto p-6 bg-slate-950/60 flex justify-center items-start">
        <div
          className="relative bg-slate-900 border border-slate-700/60 rounded-lg shadow-2xl p-8 min-h-[600px] transition-transform duration-200"
          style={{ width: `${Math.round(620 * (zoom / 100))}px`, minHeight: `${Math.round(800 * (zoom / 100))}px` }}
        >
          {/* Page Watermark Header */}
          <div className="flex justify-between items-center text-xs text-slate-500 border-b border-slate-800 pb-3 mb-6 font-mono">
            <span>{targetFilename}</span>
            <span>PAGE {currentPage}</span>
          </div>

          {/* Interactive Bounding Box Highlight Overlay */}
          {activeCitation && activeCitation.page_number === currentPage && (
            <div
              className="bbox-highlight"
              style={{
                top: `${activeCitation.bbox?.y0 ? activeCitation.bbox.y0 * (zoom / 100) : 160}px`,
                left: `${activeCitation.bbox?.x0 ? activeCitation.bbox.x0 * (zoom / 100) : 40}px`,
                width: `${activeCitation.bbox ? (activeCitation.bbox.x1 - activeCitation.bbox.x0) * (zoom / 100) : 520}px`,
                height: `${activeCitation.bbox ? Math.max(40, (activeCitation.bbox.y1 - activeCitation.bbox.y0)) * (zoom / 100) : 70}px`
              }}
            >
              <div className="absolute -top-6 left-0 bg-amber-400 text-slate-950 font-bold text-[10px] uppercase px-1.5 py-0.5 rounded shadow">
                Source Citation Highlight
              </div>
            </div>
          )}

          {/* Document Content Body */}
          <div className="space-y-4 text-slate-300 text-sm leading-relaxed font-sans">
            <h3 className="text-lg font-bold text-slate-100 border-b border-slate-800 pb-2">
              {activeCitation?.heading || `Section 4.2 - Technical Specifications`}
            </h3>

            <p className="text-slate-400">
              This document contains enterprise operational parameters, quality compliance standards, and maintenance requirements. All values are certified under ISO-9001 compliance standards.
            </p>

            {activeCitation && activeCitation.page_number === currentPage ? (
              <div className="p-4 bg-amber-500/10 border-l-4 border-amber-400 rounded-r text-amber-100 my-4 shadow-lg">
                <span className="font-semibold text-xs text-amber-400 block mb-1">VERIFIED EVIDENCE SNIPPET</span>
                "{activeCitation.text_snippet}"
              </div>
            ) : (
              <div className="p-4 bg-slate-800/40 border border-slate-700/50 rounded my-4 text-slate-300">
                Standard technical parameters, system warranty terms (5-year full replacement coverage including surge protection), cooling oil viscosity ratings (IEC 60296 compliant), and installation guidelines.
              </div>
            )}

            <div className="pt-4 border-t border-slate-800 text-xs text-slate-500 space-y-2 font-mono">
              <div className="flex justify-between">
                <span>Document ID: DOC-2026-X99</span>
                <span>Ingestion Status: OK</span>
              </div>
              <div className="flex justify-between">
                <span>Adaptive Chunking: Heading-Preserved</span>
                <span>FAISS + BM25 Indexed</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
