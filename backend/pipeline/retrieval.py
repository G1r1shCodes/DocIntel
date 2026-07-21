from sentence_transformers import SentenceTransformer, CrossEncoder
import faiss
import numpy as np
from rank_bm25 import BM25Okapi

# Initialize models
embedder = SentenceTransformer("BAAI/bge-large-en-v1.5")
cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

# Stubs for indices
# In production, these should be persisted and loaded, potentially mapped to document IDs
vector_index = None
bm25_index = None
corpus_chunks = []

def initialize_indices(chunks: list[str]):
    global vector_index, bm25_index, corpus_chunks
    corpus_chunks = chunks
    
    # Setup FAISS
    embeddings = embedder.encode(chunks)
    dimension = embeddings.shape[1]
    vector_index = faiss.IndexFlatL2(dimension)
    vector_index.add(np.array(embeddings).astype('float32'))
    
    # Setup BM25
    tokenized_chunks = [chunk.split(" ") for chunk in chunks]
    bm25_index = BM25Okapi(tokenized_chunks)

def hybrid_search(query: str, top_k: int = 10):
    """
    Performs hybrid search using FAISS (dense) and BM25 (sparse).
    """
    if not corpus_chunks:
        return []
        
    # Dense retrieval
    query_embedding = embedder.encode([query])
    D, I = vector_index.search(np.array(query_embedding).astype('float32'), top_k)
    dense_results = [corpus_chunks[i] for i in I[0]]
    
    # Sparse retrieval
    tokenized_query = query.split(" ")
    sparse_results = bm25_index.get_top_n(tokenized_query, corpus_chunks, n=top_k)
    
    # Combine unique results
    combined_results = list(set(dense_results + sparse_results))
    return combined_results

def re_rank_results(query: str, results: list[str], top_n: int = 3):
    """
    Re-ranks hybrid search results using a cross-encoder.
    """
    if not results:
        return []
        
    pairs = [[query, res] for res in results]
    scores = cross_encoder.predict(pairs)
    
    # Sort by scores
    ranked_indices = np.argsort(scores)[::-1]
    ranked_results = [results[i] for i in ranked_indices][:top_n]
    
    return ranked_results

def compress_context(query: str, ranked_chunks: list[str]):
    """
    Compresses context. A simple stub for sentence extraction or LLMLingua.
    """
    # Simple concatenation for now
    return "\n\n".join(ranked_chunks)
