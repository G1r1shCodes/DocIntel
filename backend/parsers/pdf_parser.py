"""
PDF Parser — PyMuPDF + Tesseract OCR Fallback

Extracts structured page blocks with bounding-box coordinates.
Automatically falls back to Tesseract OCR when native text density
is below a threshold.
"""

from __future__ import annotations

import io
import os

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

from .base import BaseParser, DocumentData, PageData
from .exceptions import OCRError, ParsingInterruptedError


class PDFParser(BaseParser):
    """Parse PDF documents using PyMuPDF with optional OCR fallback."""

    #: Minimum number of non-whitespace characters before we consider
    #: native text extraction successful.
    MIN_NATIVE_CHARS: int = 30
    #: DPI used when rendering pages for OCR.
    OCR_DPI: int = 150

    def supported_extensions(self) -> list[str]:
        return [".pdf"]

    def parse(self, file_path: str) -> DocumentData:
        filename = os.path.basename(file_path)
        doc = fitz.open(file_path)

        pages: list[PageData] = []
        full_text: list[str] = []

        for page_idx in range(len(doc)):
            page = doc.load_page(page_idx)
            text = page.get_text()
            text_dict = page.get_text("dict")

            blocks_data: list[dict] = []
            headings: list[str] = []
            is_ocr = False
            page_w = page.rect.width
            page_h = page.rect.height

            if len(text.strip()) < self.MIN_NATIVE_CHARS:
                # ---- OCR fallback ----
                print(
                    f"    [PDF Parser] Sparse text on page {page_idx+1}, applying OCR...",
                    flush=True,
                )
                try:
                    pix = page.get_pixmap(dpi=self.OCR_DPI)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    timeout = self.get_ocr_timeout()
                    ocr_text = pytesseract.image_to_string(img, timeout=timeout)
                    ocr_dict = pytesseract.image_to_data(
                        img, output_type=pytesseract.Output.DICT, timeout=timeout
                    )

                    text = ocr_text
                    is_ocr = True

                    n_boxes = len(ocr_dict.get("level", []))
                    for i in range(n_boxes):
                        word = ocr_dict["text"][i].strip()
                        if word:
                            blocks_data.append(
                                {
                                    "text": word,
                                    "bbox": (
                                        ocr_dict["left"][i],
                                        ocr_dict["top"][i],
                                        ocr_dict["left"][i] + ocr_dict["width"][i],
                                        ocr_dict["top"][i] + ocr_dict["height"][i],
                                    ),
                                    "type": "word",
                                }
                            )
                except Exception as exc:
                    print(f"    [PDF Parser] OCR fallback failed: {exc}", flush=True)
                    # Continue with whatever native text we have
            else:
                # ---- Native extraction ----
                for block in text_dict.get("blocks", []):
                    if block.get("type") != 0:  # 0 = text block
                        continue
                    block_text_parts: list[str] = []
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            span_text = span.get("text", "")
                            block_text_parts.append(span_text)
                            # Heading detection by font size
                            if span.get("size", 0) > 13 and span_text.strip():
                                headings.append(span_text.strip())
                    joined = " ".join(block_text_parts).strip()
                    if joined:
                        blocks_data.append(
                            {
                                "text": joined,
                                "bbox": block.get("bbox", (0, 0, 0, 0)),
                                "type": "paragraph",
                            }
                        )

            # Guard: ensure at least a paragraph block exists
            if not blocks_data and text.strip():
                blocks_data.append(
                    {
                        "text": text.strip(),
                        "bbox": (0, 0, 0, 0),
                        "type": "paragraph",
                    }
                )

            full_text.append(text)
            pages.append(
                PageData(
                    page_number=page_idx + 1,
                    text=text.strip(),
                    blocks=blocks_data,
                    headings=headings,
                    is_ocr=is_ocr,
                    page_width=page_w,
                    page_height=page_h,
                )
            )

        doc.close()

        return DocumentData(
            filename=filename,
            file_type="pdf",
            text="\n\n".join(full_text),
            metadata={
                "page_count": len(pages),
                "parser": "PyMuPDF + Tesseract OCR",
                "has_ocr_pages": any(p.is_ocr for p in pages),
            },
            pages=pages,
        )
