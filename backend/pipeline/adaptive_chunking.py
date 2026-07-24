from typing import List, Dict, Any, Optional
from parsers.base_parser import DocumentData, PageData


def adaptive_chunking(
    document: DocumentData,
    target_chunk_size: int = 600,
    overlap: int = 50,
) -> List[Dict[str, Any]]:
    """
    Hierarchical Adaptive Chunking algorithm:

    - **Preserves tables whole** (never splits table structures across chunks).
    - **Merges consecutive small blocks** under the same heading so that
      documents with many tiny blocks (e.g. resumes, structured PDFs) produce
      fewer, richer chunks rather than one chunk per line.
    - Attaches rich metadata (filename, page, heading, section, table flag,
      bounding-box coordinates).
    """
    chunks: List[Dict[str, Any]] = []
    chunk_counter = 0
    LARGE_BLOCK_THRESHOLD = int(target_chunk_size * 1.5)

    for page in document.pages:
        current_heading = "General"
        current_section = f"Page {page.page_number}"
        _page_w = page.page_width
        _page_h = page.page_height

        # Use page-level headings as default context
        if page.headings:
            current_heading = page.headings[0]

        # Accumulator for consecutive small non-heading blocks
        acc_text: str = ""
        acc_bbox: Optional[tuple] = None
        acc_first_block_idx: Optional[int] = None

        def _flush_accumulator(is_table: bool = False) -> None:
            """Flush accumulated text into a chunk."""
            nonlocal acc_text, acc_bbox, acc_first_block_idx, chunk_counter
            if not acc_text:
                return
            chunk_counter += 1
            chunks.append({
                "chunk_id": (
                    f"{document.filename}_p{page.page_number}"
                    f"_c{chunk_counter}"
                ),
                "text": acc_text.strip(),
                "heading": current_heading,
                "section": current_section,
                "page_number": page.page_number,
                "is_table": is_table,
                "bbox": acc_bbox,
                "metadata": {
                    "filename": document.filename,
                    "file_type": document.file_type,
                    "page_number": page.page_number,
                    "paragraph_id": (
                        f"p{page.page_number}_b{acc_first_block_idx}"
                        if acc_first_block_idx is not None
                        else f"p{page.page_number}_c{chunk_counter}"
                    ),
                    "is_table": is_table,
                    "_page_width": _page_w,
                    "_page_height": _page_h,
                },
            })
            acc_text = ""
            acc_bbox = None
            acc_first_block_idx = None

        for block_idx, block in enumerate(page.blocks):
            block_type = block.get("type", "paragraph")
            block_text = block.get("text", "").strip()
            bbox = block.get("bbox", None)

            if not block_text:
                continue

            # ── Case 1: Heading updates hierarchy context ──────────────
            if block_type == "heading":
                # Flush any accumulated content under the previous heading
                _flush_accumulator()
                current_heading = block_text
                current_section = f"Section: {block_text}"
                continue

            # ── Case 2: Tables remain whole ────────────────────────────
            is_table_block = (
                block_type == "table"
                or "[TABLE]" in block_text
                or block_text.startswith("Sheet:")
                or block_text.startswith("CSV File:")
            )
            if is_table_block:
                _flush_accumulator()
                chunk_counter += 1
                chunks.append({
                    "chunk_id": (
                        f"{document.filename}_p{page.page_number}"
                        f"_c{chunk_counter}"
                    ),
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
                    },
                })
                continue

            # ── Case 3: Accumulate consecutive content blocks ──────────
            # When the accumulator is non-empty, appending would exceed the
            # target size → flush first, then start a fresh accumulation.
            if acc_text and len(acc_text) + len(block_text) + 1 > target_chunk_size:
                _flush_accumulator()

            # If the block itself is larger than 1.5× target, split it by
            # sentences into multiple sub-chunks. This prevents one massive
            # paragraph from becoming an oversized chunk that would exceed
            # the embedding model's token limit (~2000 chars for 512 tokens).
            if not acc_text and len(block_text) > LARGE_BLOCK_THRESHOLD:
                sentences = [
                    s.strip()
                    for s in block_text.replace("\n", " ").split(".")
                    if s.strip()
                ]
                current_subchunk = ""
                for sentence in sentences:
                    if (
                        len(current_subchunk) + len(sentence) + 2
                        <= target_chunk_size
                    ):
                        current_subchunk += (sentence + ". ")
                    else:
                        if current_subchunk.strip():
                            acc_text = current_subchunk.strip()
                            acc_bbox = bbox
                            acc_first_block_idx = block_idx
                            _flush_accumulator()
                        current_subchunk = sentence + ". "

                if current_subchunk.strip():
                    acc_text = current_subchunk.strip()
                    acc_bbox = bbox
                    acc_first_block_idx = block_idx
                    _flush_accumulator()

                continue  # Already flushed as sub-chunks

            # Append to accumulator (normal-sized block)
            if acc_text:
                acc_text += "\n" + block_text
            else:
                acc_text = block_text
                acc_bbox = bbox  # Keep bbox of the *first* block in group
                acc_first_block_idx = block_idx

        # ── Flush any remaining accumulated content for this page ─────
        _flush_accumulator()

    # ── Fallback: if no chunks were created, use raw document text ──
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
                "is_table": False,
            },
        })

    return chunks
