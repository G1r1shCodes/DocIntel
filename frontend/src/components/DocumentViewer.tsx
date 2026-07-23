import React, { useRef, useState, useEffect, useCallback } from 'react';
import { FileText, ChevronLeft, ChevronRight, ZoomIn, ZoomOut, ExternalLink } from 'lucide-react';

interface CitationHighlight {
  page_number: number;
  filename: string;
  document_id?: number | null;
  heading?: string;
  section?: string;
  text_snippet: string;
  /** Bounding box in the PDF's native coordinate space (points). */
  bbox?: { x0: number; y0: number; x1: number; y1: number } | null;
  /** Physical page width at the time the PDF was parsed (points). */
  page_width?: number | null;
  /** Physical page height at the time the PDF was parsed (points). */
  page_height?: number | null;
}

interface DocumentViewerProps {
  filename?: string;
  activeCitation?: CitationHighlight | null;
}

/**
 * A4 at 72 DPI → 595 × 842 pt.  This is our fallback when the chunk
 * metadata didn't capture the page dimensions.
 */
const DEFAULT_PAGE_W = 595;
const DEFAULT_PAGE_H = 842;

export const DocumentViewer: React.FC<DocumentViewerProps> = ({
  filename = 'Transformer_Warranty_Manual.pdf',
  activeCitation = null,
}) => {
  const [currentPage, setCurrentPage] = useState<number>(activeCitation?.page_number || 1);
  const [zoom, setZoom] = useState<number>(100);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [overlayDims, setOverlayDims] = useState({ w: 0, h: 0 });

  const targetFilename = activeCitation?.filename || filename;
  const isPdf = targetFilename.toLowerCase().endsWith('.pdf');

  // Jump to the cited page whenever the active citation changes
  useEffect(() => {
    if (activeCitation?.page_number) {
      setCurrentPage(activeCitation.page_number);
    }
  }, [activeCitation]);

  // Compute the effective render dimensions of the PDF viewer container
  // so we can scale the bbox coordinates correctly.
  const measuredRef = useCallback((node: HTMLDivElement | null) => {
    if (node) {
      const rect = node.getBoundingClientRect();
      setOverlayDims({ w: rect.width, h: rect.height });
    }
  }, []);

  /**
   * Scale a parser-coordinate bbox to the current viewport.
   *
   * The PDF <object> fills its parent div, which is already scaled by
   * ``transform: scale(zoom/100)``.  Therefore we only need to convert
   * from PDF points to the parent's layout size (overlayDims) — the
   * zoom transform handles the rest.
   */
  const scale = (value: number, dimension: 'x' | 'y'): number => {
    const pageW = activeCitation?.page_width ?? DEFAULT_PAGE_W;
    const pageH = activeCitation?.page_height ?? DEFAULT_PAGE_H;
    const ratio = dimension === 'x' ? overlayDims.w / pageW : overlayDims.h / pageH;
    return value * ratio;
  };

  // Construct the URL for the embedded PDF viewer via the document file endpoint
  const pdfUrl = activeCitation?.document_id
    ? `/api/documents/${activeCitation.document_id}/file#page=${currentPage}`
    : undefined;

  const bboxStyle: React.CSSProperties | undefined =
    activeCitation?.bbox && activeCitation.page_number === currentPage
      ? {
          position: 'absolute',
          top: scale(activeCitation.bbox.y0, 'y'),
          left: scale(activeCitation.bbox.x0, 'x'),
          width: scale(activeCitation.bbox.x1 - activeCitation.bbox.x0, 'x'),
          height: Math.max(
            28,
            scale(activeCitation.bbox.y1 - activeCitation.bbox.y0, 'y'),
          ),
          pointerEvents: 'none' as const,
          zIndex: 10,
        }
      : undefined;

  return (
    <div className="flex flex-col h-full bg-surface-0 border border-border-subtle rounded-xl overflow-hidden shadow-sm">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-surface-0 border-b border-border-subtle shrink-0">
        <div className="flex items-center space-x-2 truncate min-w-0">
          <FileText className="w-4 h-4 text-accent shrink-0" />
          <span className="font-semibold text-sm text-text-main truncate">
            {targetFilename}
          </span>
          <span className="px-2 py-0.5 text-[10px] font-mono bg-accent-light text-accent rounded shrink-0">
            {isPdf ? 'PDF' : 'Text'}
          </span>
        </div>

        <div className="flex items-center space-x-2 text-xs shrink-0">
          {/* Page navigation */}
          <div className="flex items-center space-x-1 bg-surface-1 px-2 py-1 rounded-lg border border-border-subtle">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              className="p-0.5 hover:text-accent transition"
              title="Previous page"
              aria-label="Previous page"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <span className="font-mono px-1.5 text-text-secondary min-w-[4ch] text-center">
              {currentPage}
            </span>
            <button
              onClick={() => setCurrentPage((p) => p + 1)}
              className="p-0.5 hover:text-accent transition"
              title="Next page"
              aria-label="Next page"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Zoom controls */}
          <div className="flex items-center space-x-1 bg-surface-1 px-2 py-1 rounded-lg border border-border-subtle">
            <button
              onClick={() => setZoom((z) => Math.max(50, z - 10))}
              className="p-0.5 hover:text-accent transition"
              aria-label="Zoom out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="font-mono w-9 text-center text-text-secondary text-[11px]">
              {zoom}%
            </span>
            <button
              onClick={() => setZoom((z) => Math.min(200, z + 10))}
              className="p-0.5 hover:text-accent transition"
              aria-label="Zoom in"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* ── Citation banner ────────────────────────────────────────── */}
      {activeCitation && (
        <div className="px-4 py-2 bg-accent-light border-b border-blue-200 flex items-center justify-between text-xs text-accent shrink-0">
          <div className="flex items-center space-x-2 truncate min-w-0">
            <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse shrink-0" />
            <span className="font-semibold shrink-0">Citation:</span>
            <span className="truncate text-text-secondary">
              {activeCitation.heading || 'Section Context'}
            </span>
          </div>
          <span className="font-mono bg-white px-2 py-0.5 rounded text-accent border border-blue-200 shrink-0 font-medium ml-2">
            p.{currentPage}
          </span>
        </div>
      )}

      {/* ── Document canvas ────────────────────────────────────────── */}
      <div className="relative flex-1 overflow-auto bg-surface-1" ref={measuredRef}>
        {/* If we have a real PDF URL, embed it via <object> */}
        {isPdf ? (
          <div
            className="absolute inset-0 transition-transform duration-200 origin-top-left"
            style={{ transform: `scale(${zoom / 100})` }}
          >
            <object
              data={pdfUrl}
              type="application/pdf"
              className="w-full h-full"
              aria-label={`PDF viewer for ${targetFilename}`}
            >
              <div className="flex items-center justify-center h-full text-text-muted text-sm">
                <p>
                  PDF cannot be displayed inline.{' '}
                  <a
                    href={pdfUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-accent underline hover:no-underline"
                  >
                    Open in new tab
                  </a>
                </p>
              </div>
            </object>

            {/* ── Bbox highlight overlay ──────────────────────────────── */}
            {bboxStyle && (
              <div className="bbox-overlay" style={bboxStyle}>
                <div className="absolute -top-2.5 right-2 bg-accent text-white font-semibold text-[10px] px-2 py-0.5 rounded-full shadow-sm flex items-center space-x-1 whitespace-nowrap">
                  <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                  <span>Source Citation</span>
                </div>
              </div>
            )}
          </div>
        ) : (
          /* ── Fallback text viewer for non-PDF documents ──────────── */
          <div className="p-8 max-w-2xl mx-auto">
            <div className="bg-surface-0 border border-border-subtle rounded-lg shadow-sm p-6">
              <div className="flex items-center justify-between text-xs text-text-muted border-b border-border-subtle pb-3 mb-4 font-mono">
                <span>{targetFilename}</span>
                <span>Page {currentPage}</span>
              </div>

              <div className="space-y-4 text-text-secondary text-sm leading-relaxed">
                {activeCitation?.heading && (
                  <h3 className="text-base font-bold text-text-main border-b border-border-subtle pb-2">
                    {activeCitation.heading}
                  </h3>
                )}

                {activeCitation?.text_snippet ? (
                  <div className="p-4 bg-accent-light border-l-3 border-accent rounded-r text-accent">
                    <span className="font-semibold text-xs block mb-1">
                      EXTRACTED EVIDENCE
                    </span>
                    <span className="text-text-main">
                      &ldquo;{activeCitation.text_snippet}&rdquo;
                    </span>
                  </div>
                ) : (
                  <p className="text-text-muted italic">
                    No content available for preview.
                  </p>
                )}

                {activeCitation && (
                  <div className="pt-3 border-t border-border-subtle text-[11px] text-text-muted flex items-center gap-2">
                    <ExternalLink className="w-3 h-3" />
                    <span>
                      {targetFilename} — Page {activeCitation.page_number}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
