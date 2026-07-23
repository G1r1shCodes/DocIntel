import os
from typing import Dict, Any, List
from parsers import parse_document
from .adaptive_chunking import adaptive_chunking
from .retrieval import retriever_instance

def process_and_ingest_file(file_path: str) -> Dict[str, Any]:
    """
    Complete document ingestion pipeline:
    1. Multi-format parsing (PDF, DOCX, XLSX, CSV, TXT, Image)
    2. Adaptive Hierarchical Chunking (Heading -> Section -> Paragraph -> Sentence)
    3. Indexing into Hybrid FAISS + BM25 Retriever
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # 1. Parse document into standardized DocumentData
    print(f"  -> Parsing document...", flush=True)
    parsed_doc = parse_document(file_path)
    print(f"  -> Parsed {len(parsed_doc.pages)} pages successfully.", flush=True)

    # 2. Apply adaptive chunking
    print(f"  -> Adaptive chunking...", flush=True)
    chunks = adaptive_chunking(parsed_doc)
    print(f"  -> Created {len(chunks)} chunks.", flush=True)

    # 3. Add chunks to hybrid retriever index
    print(f"  -> Indexing chunks into hybrid retriever (FAISS + BM25)...", flush=True)
    retriever_instance.add_chunks(chunks)
    print(f"  -> Hybrid indexing finished.", flush=True)

    return {
        "filename": parsed_doc.filename,
        "file_type": parsed_doc.file_type,
        "page_count": len(parsed_doc.pages),
        "chunk_count": len(chunks),
        "metadata": parsed_doc.metadata,
        "chunks": chunks,
        "_pages": [
            {
                "page_number": p.page_number,
                "page_width": p.page_width,
                "page_height": p.page_height,
            }
            for p in parsed_doc.pages
        ],
    }
