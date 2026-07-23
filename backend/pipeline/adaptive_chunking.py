from typing import List, Dict, Any
from parsers.base_parser import DocumentData, PageData

def adaptive_chunking(document: DocumentData, target_chunk_size: int = 400, overlap: int = 50) -> List[Dict[str, Any]]:
    """
    Hierarchical Adaptive Chunking algorithm:
    - Preserves tables whole (never splits table structures across chunks)
    - Groups text hierarchically: Heading -> Section -> Paragraph -> Sentence
    - Attaches rich metadata (filename, page, heading, section, table flag, bounding box)
    """
    chunks: List[Dict[str, Any]] = []
    chunk_counter = 0

    for page in document.pages:
        current_heading = "General"
        current_section = f"Page {page.page_number}"
        # Capture page dimensions for frontend coordinate scaling
        _page_w = page.page_width
        _page_h = page.page_height

        # Track active heading from page headings if available
        if page.headings:
            current_heading = page.headings[0]

        for block_idx, block in enumerate(page.blocks):
            block_type = block.get("type", "paragraph")
            block_text = block.get("text", "").strip()
            bbox = block.get("bbox", None)

            if not block_text:
                continue

            # Case 1: Heading updates hierarchy context
            if block_type == "heading":
                current_heading = block_text
                current_section = f"Section: {block_text}"
                continue

            # Case 2: Tables remain whole
            if block_type == "table" or "[TABLE]" in block_text or block_text.startswith("Sheet:") or block_text.startswith("CSV File:"):
                chunk_counter += 1
                chunks.append({
                    "chunk_id": f"{document.filename}_p{page.page_number}_c{chunk_counter}",
                    "text": block_text,
                    "heading": current_heading,
                    "section": current_section,
                    "page_number": page.page_number,
                    "is_table": True,
                    "bbox": bbox,
                    "metadata": {
                        "filename": document.filename,
                        "file_type": document.file_type,
                        "page_number": page.page_number,
                        "paragraph_id": f"p{page.page_number}_b{block_idx}",
                        "is_table": True,
                        "_page_width": _page_w,
                        "_page_height": _page_h,
                    }
                })
                continue

            # Case 3: Paragraph/Sentence adaptive splitting
            if len(block_text) <= target_chunk_size:
                chunk_counter += 1
                chunks.append({
                    "chunk_id": f"{document.filename}_p{page.page_number}_c{chunk_counter}",
                    "text": block_text,
                    "heading": current_heading,
                    "section": current_section,
                    "page_number": page.page_number,
                    "is_table": False,
                    "bbox": bbox,
                    "metadata": {
                        "filename": document.filename,
                        "file_type": document.file_type,
                        "page_number": page.page_number,
                        "paragraph_id": f"p{page.page_number}_b{block_idx}",
                        "is_table": False,
                        "_page_width": _page_w,
                        "_page_height": _page_h,
                    }
                })
            else:
                # Split large paragraphs into sentences or sub-chunks
                sentences = [s.strip() for s in block_text.replace("\n", " ").split(".") if s.strip()]
                current_subchunk = ""
                
                for sentence in sentences:
                    if len(current_subchunk) + len(sentence) + 2 <= target_chunk_size:
                        current_subchunk += (sentence + ". ")
                    else:
                        if current_subchunk.strip():
                            chunk_counter += 1
                            chunks.append({
                                "chunk_id": f"{document.filename}_p{page.page_number}_c{chunk_counter}",
                                "text": current_subchunk.strip(),
                                "heading": current_heading,
                                "section": current_section,
                                "page_number": page.page_number,
                                "is_table": False,
                                "bbox": bbox,
                                "metadata": {
                                    "filename": document.filename,
                                    "file_type": document.file_type,
                                    "page_number": page.page_number,
                                    "paragraph_id": f"p{page.page_number}_b{block_idx}",
                                    "is_table": False
                                }
                            })
                        current_subchunk = sentence + ". "

                if current_subchunk.strip():
                    chunk_counter += 1
                    chunks.append({
                        "chunk_id": f"{document.filename}_p{page.page_number}_c{chunk_counter}",
                        "text": current_subchunk.strip(),
                        "heading": current_heading,
                        "section": current_section,
                        "page_number": page.page_number,
                        "is_table": False,
                        "bbox": bbox,
                        "metadata": {
                            "filename": document.filename,
                            "file_type": document.file_type,
                            "page_number": page.page_number,
                            "paragraph_id": f"p{page.page_number}_b{block_idx}",
                            "is_table": False
                        }
                    })

    if not chunks and document.text and document.text.strip():
        chunks.append({
            "chunk_id": f"{document.filename}_p1_c1",
            "text": document.text.strip()[:1000],
            "heading": "General",
            "section": "Document Content",
            "page_number": 1,
            "is_table": False,
            "bbox": (0, 0, 0, 0),
            "metadata": {
                "filename": document.filename,
                "file_type": document.file_type,
                "page_number": 1,
                "paragraph_id": "p1_b0",
                "is_table": False
            }
        })

    return chunks
