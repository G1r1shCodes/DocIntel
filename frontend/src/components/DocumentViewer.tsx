import React, { useState } from 'react';
import { FileText, ChevronLeft, ChevronRight, ZoomIn, ZoomOut } from 'lucide-react';

interface CitationHighlight {
  page_number: number;
  filename: string;
  heading?: string;
  text_snippet: string;
  bbox?: { x0: number; y0: number; x1: number; y1: number };
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
    if (activeCitation?.page_number) setCurrentPage(activeCitation.page_number);
  }, [activeCitation]);

  const targetFilename = activeCitation?.filename || filename;
  const isPdf = targetFilename.toLowerCase().endsWith('.pdf');

  return (
    <div className="flex flex-col h-full bg-surface-0 border border-border-subtle rounded-xl overflow-hidden shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-surface-0 border-b border-border-subtle">
        <div className="flex items-center space-x-2 truncate">
          <FileText className="w-4 h-4 text-accent shrink-0" />
          <span className="font-semibold text-sm text-text-main truncate">{targetFilename}</span>
          <span className="px-2 py-0.5 text-xs font-mono bg-accent-light text-accent rounded">
            {isPdf ? 'PDF' : 'Text'}
          </span>
        </div>
        <div className="flex items-center space-x-2 text-xs">
          <div className="flex items-center space-x-1 bg-surface-1 px-2 py-1 rounded-lg border border-border-subtle">
            <button onClick={() => setCurrentPage((p) => Math.max(1, p - 1))} className="p-0.5 hover:text-accent transition" title="Previous Page">
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <span className="font-mono px-1.5 text-text-secondary">Page {currentPage}</span>
            <button onClick={() => setCurrentPage((p) => p + 1)} className="p-0.5 hover:text-accent transition" title="Next Page">
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="flex items-center space-x-1 bg-surface-1 px-2 py-1 rounded-lg border border-border-subtle">
            <button onClick={() => setZoom((z) => Math.max(50, z - 10))} className="p-0.5 hover:text-accent transition">
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="font-mono w-9 text-center text-text-secondary">{zoom}%</span>
            <button onClick={() => setZoom((z) => Math.min(200, z + 10))} className="p-0.5 hover:text-accent transition">
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Citation Banner */}
      {activeCitation && (
        <div className="px-4 py-2 bg-accent-light border-b border-blue-200 flex items-center justify-between text-xs text-accent">
          <div className="flex items-center space-x-2 truncate">
            <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
            <span className="font-semibold">Citation Active:</span>
            <span className="truncate text-text-secondary">{activeCitation.heading || 'Section Context'}</span>
          </div>
          <span className="font-mono bg-white px-2 py-0.5 rounded text-accent border border-blue-200 shrink-0 font-medium">
            Page {activeCitation.page_number}
          </span>
        </div>
      )}

      {/* Document Canvas */}
      <div className="relative flex-1 overflow-auto p-6 bg-surface-1 flex justify-center items-start">
        <div
          className="relative bg-surface-0 border border-border-subtle rounded-lg shadow-sm p-8 min-h-[600px] transition-transform duration-200"
          style={{ width: `${Math.round(620 * (zoom / 100))}px`, minHeight: `${Math.round(800 * (zoom / 100))}px` }}
        >
          <div className="flex justify-between items-center text-xs text-text-muted border-b border-border-subtle pb-3 mb-6 font-mono">
            <span>{targetFilename}</span>
            <span>PAGE {currentPage}</span>
          </div>

          {activeCitation && activeCitation.page_number === currentPage && (
            <div
              className="bbox-overlay"
              style={{
                top: `${activeCitation.bbox?.y0 ? activeCitation.bbox.y0 * (zoom / 100) : 205}px`,
                left: `${activeCitation.bbox?.x0 ? activeCitation.bbox.x0 * (zoom / 100) : 32}px`,
                width: `${activeCitation.bbox ? (activeCitation.bbox.x1 - activeCitation.bbox.x0) * (zoom / 100) : 556}px`,
                height: `${activeCitation.bbox ? Math.max(40, (activeCitation.bbox.y1 - activeCitation.bbox.y0)) * (zoom / 100) : 90}px`
              }}
            >
              <div className="absolute -top-2.5 right-3 bg-accent text-white font-semibold text-[10px] px-2 py-0.5 rounded-full shadow-sm flex items-center space-x-1">
                <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                <span>Source Citation</span>
              </div>
            </div>
          )}

          <div className="space-y-4 text-text-secondary text-sm leading-relaxed">
            <h3 className="text-lg font-bold text-text-main border-b border-border-subtle pb-2">
              {activeCitation?.heading || `Section 4.2 - Technical Specifications`}
            </h3>
            <p>
              This document contains enterprise operational parameters, quality compliance standards, and maintenance requirements. All values are certified under ISO-9001 compliance standards.
            </p>
            {activeCitation && activeCitation.page_number === currentPage ? (
              <div className="p-4 bg-accent-light border-l-3 border-accent rounded-r text-accent my-4">
                <span className="font-semibold text-xs block mb-1">VERIFIED EVIDENCE</span>
                <span className="text-text-main">"{activeCitation.text_snippet}"</span>
              </div>
            ) : (
              <div className="p-4 bg-surface-1 border border-border-subtle rounded my-4 text-text-secondary">
                Standard technical parameters, system warranty terms (5-year full replacement coverage including surge protection), cooling oil viscosity ratings (IEC 60296 compliant), and installation guidelines.
              </div>
            )}
            <div className="pt-4 border-t border-border-subtle text-xs text-text-muted space-y-2 font-mono">
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
