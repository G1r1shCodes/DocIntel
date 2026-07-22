import os
import pytesseract
from PIL import Image
from .base_parser import DocumentData, PageData

def parse_image(file_path: str) -> DocumentData:
    """
    Parses Image files (PNG, JPG, TIFF, BMP) using Tesseract OCR with bounding boxes.
    """
    filename = os.path.basename(file_path)
    text = ""
    blocks = []

    try:
        img = Image.open(file_path)
        text = pytesseract.image_to_string(img)
        ocr_dict = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        
        n_boxes = len(ocr_dict.get('level', []))
        for i in range(n_boxes):
            word = ocr_dict['text'][i].strip()
            if word:
                blocks.append({
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
        text = f"Image OCR Error: {str(e)}"

    page = PageData(
        page_number=1,
        text=text.strip(),
        blocks=blocks,
        headings=[filename],
        is_ocr=True
    )

    return DocumentData(
        filename=filename,
        file_type="image",
        text=text.strip(),
        metadata={"parser": "Tesseract OCR", "blocks_count": len(blocks)},
        pages=[page]
    )
