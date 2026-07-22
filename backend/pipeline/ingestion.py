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
    parsed_doc = parse_document(file_path)

    # 2. Apply adaptive chunking
    chunks = adaptive_chunking(parsed_doc)

    # 3. Add chunks to hybrid retriever index
    retriever_instance.add_chunks(chunks)

    return {
        "filename": parsed_doc.filename,
        "file_type": parsed_doc.file_type,
        "page_count": len(parsed_doc.pages),
        "chunk_count": len(chunks),
        "metadata": parsed_doc.metadata,
        "chunks": chunks
    }
