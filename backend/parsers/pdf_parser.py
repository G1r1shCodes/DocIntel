import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import os
from typing import Dict, Any
from .base_parser import DocumentData, PageData

def parse_pdf(file_path: str) -> DocumentData:
    """
    Parses a PDF using PyMuPDF native extraction with pytesseract OCR fallback.
    Extracts structured page blocks with bounding box coordinates.
    """
    filename = os.path.basename(file_path)
    doc = fitz.open(file_path)
    pages: list[PageData] = []
    full_text_list = []

    for page_idx in range(len(doc)):
        page = doc.load_page(page_idx)
        text = page.get_text()
        text_dict = page.get_text("dict")
        
        blocks_data = []
        headings = []
        is_ocr = False

        # If native text extraction is sparse, apply OCR
        if len(text.strip()) < 30:
            try:
                pix = page.get_pixmap(dpi=150)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                ocr_text = pytesseract.image_to_string(img)
                ocr_dict = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                
                text = ocr_text
                is_ocr = True
                
                n_boxes = len(ocr_dict.get('level', []))
                for i in range(n_boxes):
                    word = ocr_dict['text'][i].strip()
                    if word:
                        blocks_data.append({
                            "text": word,
                            "bbox": (
                                ocr_dict['left'][i],
                                ocr_dict['top'][i],
                                ocr_dict['left'][i] + ocr_dict['width'][i],
                                ocr_dict['top'][i] + ocr_dict['height'][i]
                            ),
                            "type": "word"
                        })
            except Exception as e:
                # OCR fallback fail resilience
                pass
        else:
            # Process PyMuPDF dict blocks
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:  # text block
                    block_text = ""
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            span_text = span.get("text", "")
                            block_text += span_text + " "
                            # Check font size for heading detection
                            if span.get("size", 0) > 13 and span_text.strip():
                                headings.append(span_text.strip())
                    
                    if block_text.strip():
                        blocks_data.append({
                            "text": block_text.strip(),
                            "bbox": block.get("bbox", (0, 0, 0, 0)),
                            "type": "paragraph"
                        })

        full_text_list.append(text)
        pages.append(PageData(
            page_number=page_idx + 1,
            text=text.strip(),
            blocks=blocks_data,
            headings=headings,
            is_ocr=is_ocr
        ))

    doc.close()
    
    metadata = {
        "page_count": len(pages),
        "parser": "PyMuPDF + Tesseract OCR",
        "has_ocr_pages": any(p.is_ocr for p in pages)
    }

    return DocumentData(
        filename=filename,
        file_type="pdf",
        text="\n\n".join(full_text_list),
        metadata=metadata,
        pages=pages
    )
