import numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer, CrossEncoder
import faiss
from rank_bm25 import BM25Okapi
import logging

logger = logging.getLogger(__name__)

# Initialize models lazily or globally
_embedder = None
_cross_encoder = None

def get_embedder():
    global _embedder
    if _embedder is None:
        try:
            _embedder = SentenceTransformer("BAAI/bge-small-en-v1.5")
        except Exception as e:
            logger.warning(f"Could not load BGE model, using all-MiniLM-L6-v2 fallback: {e}")
            _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder

def get_cross_encoder():
    global _cross_encoder
    if _cross_encoder is None:
        try:
            _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        except Exception as e:
            logger.warning(f"Could not load CrossEncoder: {e}")
            _cross_encoder = None
    return _cross_encoder


class HybridRetriever:
    def __init__(self):
        self.chunks: List[Dict[str, Any]] = []
        self.vector_index = None
        self.bm25_index = None
        self.embeddings = None

    def index_chunks(self, chunks: List[Dict[str, Any]]):
        """
        Indexes a list of structured chunk dicts into FAISS (dense) and BM25 (sparse).
        """
        if not chunks:
            return
        
        self.chunks = chunks
        embedder = get_embedder()
        
        # Dense indexing via SentenceTransformer & FAISS
        texts = [c["text"] for c in chunks]
        embeddings = embedder.encode(texts, show_progress_bar=False)
        self.embeddings = np.array(embeddings).astype("float32")
        
        dimension = self.embeddings.shape[1]
        self.vector_index = faiss.IndexFlatL2(dimension)
        self.vector_index.add(self.embeddings)

        # Sparse indexing via BM25
        tokenized_corpus = [t.lower().split() for t in texts]
        self.bm25_index = BM25Okapi(tokenized_corpus)

    def add_chunks(self, new_chunks: List[Dict[str, Any]]):
        """
        Appends new chunks to existing index.
        """
        all_chunks = self.chunks + new_chunks
        self.index_chunks(all_chunks)

    def hybrid_search(self, query: str, top_k_dense: int = 20, top_k_sparse: int = 20, top_n_rerank: int = 5) -> List[Dict[str, Any]]:
        """
        Executes dense FAISS + sparse BM25 hybrid search, RRF rank fusion, cross-encoder re-ranking (Top 30 -> Top 5).
        """
        if not self.chunks or self.vector_index is None:
            return []

        # 1. Dense retrieval
        embedder = get_embedder()
        query_vector = embedder.encode([query]).astype("float32")
        distances, dense_indices = self.vector_index.search(query_vector, min(top_k_dense, len(self.chunks)))
        
        # 2. Sparse retrieval
        tokenized_query = query.lower().split()
        bm25_scores = self.bm25_index.get_scores(tokenized_query)
        sparse_indices = np.argsort(bm25_scores)[::-1][:min(top_k_sparse, len(self.chunks))]

        # 3. Reciprocal Rank Fusion (RRF)
        rrf_scores: Dict[int, float] = {}
        k = 60
        
        for rank, idx in enumerate(dense_indices[0]):
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + 1.0 / (k + rank + 1)

        for rank, idx in enumerate(sparse_indices):
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + 1.0 / (k + rank + 1)

        # Sort top candidate indices by RRF score
        sorted_candidate_indices = sorted(rrf_scores.keys(), key=lambda i: rrf_scores[i], reverse=True)[:30]
        candidate_chunks = [self.chunks[i] for i in sorted_candidate_indices]

        # 4. Cross-Encoder Re-Ranking (Top 30 -> Top 5)
        cross_enc = get_cross_encoder()
        if cross_enc and candidate_chunks:
            pairs = [[query, c["text"]] for c in candidate_chunks]
            scores = cross_enc.predict(pairs)
            ranked_indices = np.argsort(scores)[::-1][:top_n_rerank]
            final_reranked = [candidate_chunks[i] for i in ranked_indices]
        else:
            final_reranked = candidate_chunks[:top_n_rerank]

        return final_reranked


def compress_context(query: str, retrieved_chunks: List[Dict[str, Any]], max_chars: int = 1500) -> str:
    """
    Compresses retrieved context to essential paragraphs to reduce LLM prompt size.
    """
    compressed_text_blocks = []
    total_length = 0

    for chunk in retrieved_chunks:
        text = chunk.get("text", "")
        heading = chunk.get("heading", "General")
        page = chunk.get("page_number", 1)
        filename = chunk.get("metadata", {}).get("filename", "document")
        
        header_info = f"[Source: {filename} | Page {page} | {heading}]"
        block = f"{header_info}\n{text}"

        if total_length + len(block) > max_chars:
            break
            
        compressed_text_blocks.append(block)
        total_length += len(block)

    return "\n\n---\n\n".join(compressed_text_blocks)

# Global retriever instance
retriever_instance = HybridRetriever()
