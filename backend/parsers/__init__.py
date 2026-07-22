import os
from .base_parser import DocumentData
from .pdf_parser import parse_pdf
from .docx_parser import parse_docx
from .excel_parser import parse_excel
from .csv_parser import parse_csv
from .image_parser import parse_image
from .txt_parser import parse_txt

def parse_document(file_path: str) -> DocumentData:
    """
    Unified entrypoint router for multi-format document parsing.
    Supports PDF, DOCX, XLSX, CSV, TXT, and Images.
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == ".pdf":
        return parse_pdf(file_path)
    elif ext in [".docx", ".doc"]:
        return parse_docx(file_path)
    elif ext in [".xlsx", ".xls"]:
        return parse_excel(file_path)
    elif ext == ".csv":
        return parse_csv(file_path)
    elif ext in [".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"]:
        return parse_image(file_path)
    elif ext in [".txt", ".md", ".json", ".log"]:
        return parse_txt(file_path)
    else:
        # Fallback to plain text reading
        return parse_txt(file_path)
