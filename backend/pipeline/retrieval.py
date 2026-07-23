"""
Hybrid Retriever — FAISS Dense + BM25 Sparse + Cross-Encoder Reranker

Supports incremental add (without full rebuild), ID-based removal
via ``faiss.IndexIDMap``, and full index serialisation to disk so
that the retriever state survives application restarts.
"""

from __future__ import annotations

import os
import pickle
import logging
from pathlib import Path
from typing import Any, List, Dict

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder, SentenceTransformer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy model initialisation
# ---------------------------------------------------------------------------

_embedder: SentenceTransformer | None = None
_cross_encoder: CrossEncoder | None = None

_INDEX_DIR = os.environ.get(
    "DOCINTEL_INDEX_DIR",
    str(Path(__file__).resolve().parent.parent / "index_data"),
)


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        try:
            _embedder = SentenceTransformer("BAAI/bge-small-en-v1.5")
        except Exception as exc:
            logger.warning("Could not load BGE model, using all-MiniLM-L6-v2 fallback: %s", exc)
            _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def get_cross_encoder() -> CrossEncoder | None:
    global _cross_encoder
    if _cross_encoder is None:
        try:
            _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        except Exception as exc:
            logger.warning("Could not load CrossEncoder: %s", exc)
    return _cross_encoder


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------

class HybridRetriever:
    """
    Hybrid sparse-dense retriever with cross-encoder re-ranking.

    **FAISS index layout** (``IndexIDMap``):
    Each chunk receives a unique monotonically increasing ``faiss_id``
    stored in ``chunk["metadata"]["faiss_id"]``.  This lets us remove
    all vectors belonging to a document in a single ``remove_ids()``
    call *without* rebuilding the entire index.
    """

    _INDEX_FILE = "faiss.index"
    _DATA_FILE = "retriever_data.pkl"

    def __init__(self) -> None:
        self.chunks: list[dict[str, Any]] = []
        self.vector_index: faiss.IndexIDMap | None = None
        self.bm25_index: BM25Okapi | None = None
        self._next_faiss_id: int = 0

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def index_chunks(self, chunks: list[dict[str, Any]]) -> None:
        """Full re-index — replaces *all* existing data with *chunks*."""
        if not chunks:
            return
        self.chunks = []
        self.vector_index = None
        self.bm25_index = None
        self.embeddings = None
        self._next_faiss_id = 0
        self.add_chunks(chunks)

    def add_chunks(self, new_chunks: list[dict[str, Any]]) -> None:
        """
        Incrementally append *new_chunks* to the existing index.

        FAISS is updated in-place (no re-encoding of old chunks).  BM25
        **must** be rebuilt from scratch because ``BM25Okapi`` does not
        support incremental addition.
        """
        if not new_chunks:
            return

        embedder = get_embedder()
        texts = [c["text"] for c in new_chunks]
        embeddings = embedder.encode(texts, show_progress_bar=False)
        float_emb = np.array(embeddings).astype("float32")

        # Assign unique FAISS IDs
        count = len(new_chunks)
        faiss_ids = np.arange(
            self._next_faiss_id,
            self._next_faiss_id + count,
            dtype=np.int64,
        )
        self._next_faiss_id += count

        # Create or extend the FAISS index
        if self.vector_index is None:
            dimension = float_emb.shape[1]
            flat_index = faiss.IndexFlatL2(dimension)
            self.vector_index = faiss.IndexIDMap(flat_index)

        self.vector_index.add_with_ids(float_emb, faiss_ids)

        # Store the FAISS id back into each chunk's metadata
        for i, chunk in enumerate(new_chunks):
            chunk.setdefault("metadata", {})["faiss_id"] = int(faiss_ids[i])

        self.chunks.extend(new_chunks)

        # Rebuild BM25 (full corpus)
        all_texts = [c["text"] for c in self.chunks]
        self.bm25_index = BM25Okapi([t.lower().split() for t in all_texts])

        self._save()

    # ------------------------------------------------------------------
    # Metadata updates (called after DB persistence)
    # ------------------------------------------------------------------

    def update_chunk_metadata(
        self, filename: str, db_ids: list[int], document_id: int
    ) -> None:
        """
        Stamp in-memory chunks with their database primary keys **after**
        the document row has been committed.
        """
        matched = 0
        db_idx = 0
        for chunk in self.chunks:
            meta = chunk.setdefault("metadata", {})
            if meta.get("filename") == filename and db_idx < len(db_ids):
                meta["chunk_db_id"] = db_ids[db_idx]
                meta["document_id"] = document_id
                db_idx += 1
                matched += 1
        if matched:
            logger.info(
                "Updated chunk metadata for %s: doc_id=%d (%d / %d chunks)",
                filename, document_id, matched, len(db_ids),
            )
            self._save()

    # ------------------------------------------------------------------
    # Removal
    # ------------------------------------------------------------------

    def remove_chunks_by_document_id(self, document_id: int) -> bool:
        """
        Remove all chunks belonging to *document_id* using their FAISS
        IDs, then rebuild BM25.  Returns ``True`` if any chunks were
        actually removed.
        """
        if not self.chunks:
            return False

        to_remove: list[int] = []
        kept: list[dict[str, Any]] = []

        for chunk in self.chunks:
            if chunk.get("metadata", {}).get("document_id") == document_id:
                fid = chunk.get("metadata", {}).get("faiss_id")
                if fid is not None:
                    to_remove.append(fid)
            else:
                kept.append(chunk)

        if not to_remove:
            return False

        # FAISS ID-based removal (avoids full rebuild of the dense index)
        if self.vector_index is not None:
            self.vector_index.remove_ids(np.array(to_remove, dtype=np.int64))

        # Rebuild BM25 (no incremental remove support)
        self.chunks = kept
        if kept:
            texts = [c["text"] for c in kept]
            self.bm25_index = BM25Okapi([t.lower().split() for t in texts])
        else:        self.chunks.clear()
        self.bm25_index = None

        self._save()
        logger.info("Removed %d chunks for document_id=%d", len(to_remove), document_id)
        return True

    def remove_chunks_by_filename(self, filename: str) -> None:
        """
        Legacy removal by filename — rebuilds the full index.
        Prefer :meth:`remove_chunks_by_document_id` when possible.
        """
        if not self.chunks:
            return

        filtered = [
            c for c in self.chunks
            if c.get("metadata", {}).get("filename") != filename
        ]
        if len(filtered) == len(self.chunks):
            return

        self.chunks.clear()
        self.vector_index = None
        self.bm25_index = None
        self._next_faiss_id = 0

        self.index_chunks(filtered)
        self._save()

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def hybrid_search(
        self,
        query: str,
        top_k_dense: int = 20,
        top_k_sparse: int = 20,
        top_n_rerank: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Execute dense FAISS + sparse BM25 hybrid search with RRF fusion
        and cross-encoder re-ranking (top 30 → top 5).
        """
        if not self.chunks or self.vector_index is None or self.bm25_index is None:
            return []

        embedder = get_embedder()

        # 1. Dense retrieval
        query_vec = embedder.encode([query]).astype("float32")
        distances, dense_indices = self.vector_index.search(
            query_vec, min(top_k_dense, len(self.chunks)),
        )

        # 2. Sparse retrieval
        tok_query = query.lower().split()
        bm25_scores = self.bm25_index.get_scores(tok_query)
        sparse_indices = np.argsort(bm25_scores)[::-1][:min(top_k_sparse, len(self.chunks))]

        # Map FAISS IDs to array indices
        faiss_to_idx = {c.get("metadata", {}).get("faiss_id"): i for i, c in enumerate(self.chunks) if c.get("metadata", {}).get("faiss_id") is not None}

        # 3. RRF fusion
        rrf: dict[int, float] = {}
        k = 60
        for rank, faiss_id in enumerate(dense_indices[0]):
            # faiss_id can be -1 if FAISS returns empty slots (e.g., when index has fewer than top_k items)
            if faiss_id in faiss_to_idx:
                idx = faiss_to_idx[faiss_id]
                rrf[idx] = rrf.get(idx, 0.0) + 1.0 / (k + rank + 1)
        for rank, idx in enumerate(sparse_indices):
            rrf[idx] = rrf.get(idx, 0.0) + 1.0 / (k + rank + 1)

        sorted_candidates = sorted(rrf, key=rrf.__getitem__, reverse=True)[:30]
        candidate_chunks = [self.chunks[i] for i in sorted_candidates]

        # 4. Cross-encoder re-ranking
        cross_enc = get_cross_encoder()
        if cross_enc and candidate_chunks:
            pairs = [[query, c["text"]] for c in candidate_chunks]
            scores = cross_enc.predict(pairs)
            reranked = np.argsort(scores)[::-1][:top_n_rerank]
            return [candidate_chunks[i] for i in reranked]

        return candidate_chunks[:top_n_rerank]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _index_path(self) -> Path:
        os.makedirs(_INDEX_DIR, exist_ok=True)
        return Path(_INDEX_DIR) / self._INDEX_FILE

    def _data_path(self) -> Path:
        os.makedirs(_INDEX_DIR, exist_ok=True)
        return Path(_INDEX_DIR) / self._DATA_FILE

    def _save(self) -> None:
        """
        Persist FAISS index + chunk data + BM25 state to disk.
        Safe to call after every mutating operation (add / remove).
        """
        try:
            if self.vector_index is not None:
                faiss.write_index(self.vector_index, str(self._index_path()))

            data = {
                "chunks": self.chunks,
                "bm25_corpus": [c["text"] for c in self.chunks],
                "_next_faiss_id": self._next_faiss_id,
            }
            with open(self._data_path(), "wb") as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as exc:
            logger.error("Failed to persist retriever index: %s", exc)

    def load(self) -> None:
        """
        Restore a previously persisted index from disk.  Called during
        application startup (see ``main.py``).
        """
        idx_path = self._index_path()
        data_path = self._data_path()

        if not idx_path.exists() or not data_path.exists():
            logger.info("No persisted index found — starting with empty retriever.")
            return

        try:
            self.vector_index = faiss.read_index(str(idx_path))

            with open(data_path, "rb") as f:
                data: dict = pickle.load(f)

            self.chunks = data.get("chunks", [])
            self._next_faiss_id = data.get("_next_faiss_id", 0)

            # Rebuild BM25 from saved corpus
            if self.chunks:
                texts = [c["text"] for c in self.chunks]
                self.bm25_index = BM25Okapi([t.lower().split() for t in texts])

            logger.info(
                "Loaded persisted index: %d chunks, next FAISS id = %d",
                len(self.chunks),
                self._next_faiss_id,
            )
        except Exception as exc:
            logger.error("Failed to load persisted index: %s — starting fresh.", exc)
            self.chunks.clear()
            self.vector_index = None
            self.bm25_index = None


# ---------------------------------------------------------------------------
# Singleton & context compression helper
# ---------------------------------------------------------------------------

retriever_instance = HybridRetriever()


def compress_context(
    query: str,
    retrieved_chunks: list[dict[str, Any]],
    max_chars: int = 1500,
) -> str:
    """Join retrieved chunks into a single context string for the LLM."""
    blocks: list[str] = []
    total = 0
    for idx, chunk in enumerate(retrieved_chunks):
        text = chunk.get("text", "")
        heading = chunk.get("heading", "General")
        page = chunk.get("page_number", 1)
        filename = chunk.get("metadata", {}).get("filename", "document")
        block = f"[Source {idx + 1}: {filename} | Page {page} | {heading}]\n{text}"
        if total + len(block) > max_chars:
            break
        blocks.append(block)
        total += len(block)
    return "\n\n---\n\n".join(blocks)
