import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io

def parse_pdf(file_path: str):
    """
    Parses a PDF, extracting text and bounding boxes.
    Uses OCR fallback if text is not present.
    """
    doc = fitz.open(file_path)
    pages_data = []
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text_dict = page.get_text("dict")
        text = page.get_text()
        
        # If very little text, assume scanned and use OCR fallback
        if not text.strip():
            pix = page.get_pixmap()
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            # Get data with bounding boxes
            ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            
            blocks = []
            n_boxes = len(ocr_data['level'])
            for i in range(n_boxes):
                if ocr_data['text'][i].strip():
                    blocks.append({
                        "text": ocr_data['text'][i],
                        "bbox": (
                            ocr_data['left'][i], 
                            ocr_data['top'][i], 
                            ocr_data['left'][i] + ocr_data['width'][i], 
                            ocr_data['top'][i] + ocr_data['height'][i]
                        )
                    })
            
            pages_data.append({
                "page": page_num + 1,
                "text": pytesseract.image_to_string(img),
                "blocks": blocks,
                "is_ocr": True
            })
        else:
            pages_data.append({
                "page": page_num + 1,
                "text": text,
                "blocks": text_dict.get("blocks", []),
                "is_ocr": False
            })
            
    return pages_data

def adaptive_chunking(pages_data):
    """
    Chunks text based on semantic boundaries (headings/paragraphs)
    """
    chunks = []
    # TODO: Implement semantic chunking using Unstructured/Langchain
    return chunks
