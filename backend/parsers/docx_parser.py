import os
from typing import List
from .base_parser import DocumentData, PageData

def parse_docx(file_path: str) -> DocumentData:
    """
    Parses a DOCX Word document preserving headings, paragraphs, and tables.
    """
    filename = os.path.basename(file_path)
    full_text_list = []
    blocks_data = []
    headings = []

    try:
        import docx
        doc = docx.Document(file_path)

        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue
            
            if p.style and 'heading' in p.style.name.lower():
                headings.append(text)
                blocks_data.append({"text": text, "type": "heading", "style": p.style.name})
            else:
                blocks_data.append({"text": text, "type": "paragraph"})
            
            full_text_list.append(text)

        # Parse tables
        for table_idx, table in enumerate(doc.tables):
            table_rows = []
            for row in table.rows:
                row_data = [cell.text.strip() for cell in row.cells]
                table_rows.append(" | ".join(row_data))
            
            table_str = "\n".join(table_rows)
            if table_str.strip():
                full_text_list.append(f"[TABLE]\n{table_str}\n[/TABLE]")
                blocks_data.append({
                    "text": table_str,
                    "type": "table",
                    "table_index": table_idx
                })

    except ImportError:
        # Fallback text reading if docx library is not available
        with open(file_path, "rb") as f:
            raw_content = f.read().decode("utf-8", errors="ignore")
            full_text_list.append(raw_content)
            blocks_data.append({"text": raw_content, "type": "raw"})

    combined_text = "\n\n".join(full_text_list)
    page_data = PageData(
        page_number=1,
        text=combined_text,
        blocks=blocks_data,
        headings=headings,
        is_ocr=False
    )

    return DocumentData(
        filename=filename,
        file_type="docx",
        text=combined_text,
        metadata={"parser": "python-docx", "paragraph_count": len(blocks_data)},
        pages=[page_data]
    )
