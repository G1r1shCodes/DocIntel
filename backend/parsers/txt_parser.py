import os
from .base_parser import DocumentData, PageData

def parse_txt(file_path: str) -> DocumentData:
    """
    Parses plain text files (.txt, .md, .log, .json).
    """
    filename = os.path.basename(file_path)
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    lines = text.splitlines()
    blocks = [{"text": line, "type": "paragraph"} for line in lines if line.strip()]
    headings = [line.strip("# ").strip() for line in lines if line.startswith("#")]

    page = PageData(
        page_number=1,
        text=text,
        blocks=blocks,
        headings=headings,
        is_ocr=False
    )

    return DocumentData(
        filename=filename,
        file_type="txt",
        text=text,
        metadata={"parser": "text/utf-8", "line_count": len(lines)},
        pages=[page]
    )
