# pylint: disable=import-error
"""Compare vector-only vs hybrid vs hybrid+rerank retrieval quality."""

import numpy as np
from bm25 import BM25
from models import SearchResult
from recall import fuse_candidates
from reranker import CrossEncoderReranker


def precision_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Fraction of top-k results that are relevant."""
    if not retrieved_ids:
        return 0.0
    top_k = retrieved_ids[:k]
    hits = sum(1 for i in top_k if i in relevant_ids)
    return hits / len(top_k)


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = np.dot(v1, v2)
    norm = np.linalg.norm(v1) * np.linalg.norm(v2)
    return dot / norm if norm > 0 else 0.0


def _vector_recall(
    query: str, chunks: list, embedder, top_k: int
) -> list[SearchResult]:
    """Return top-k chunks by vector similarity."""
    qv = embedder.get_embedding(query)
    scored = []
    for c in chunks:
        sim = _cosine_similarity(qv, c.embedding)
        scored.append(SearchResult(chunk=c, score=sim, search_type="vector"))
    scored.sort(key=lambda x: x.score, reverse=True)
    return scored[:top_k]


def _keyword_recall(query: str, chunks: list, top_k: int) -> list[SearchResult]:
    """Return top-k chunks by BM25 score."""
    bm25 = BM25()
    bm25.fit([c.text for c in chunks])
    hits = bm25.top_k(query, k=top_k)
    return [
        SearchResult(chunk=chunks[i], score=s, search_type="keyword") for i, s in hits
    ]


def compare_strategies(
    query: str,
    relevant_ids: set[str],
    chunks: list,
    embedder,
    k: int = 3,
) -> dict:
    """Run all three strategies and score them."""
    # 1. Vector only
    vec_results = _vector_recall(query, chunks, embedder, top_k=k)
    vec_ids = [r.chunk.id for r in vec_results]

    # 2. Hybrid (recall fusion, no rerank)
    v_hits = _vector_recall(query, chunks, embedder, top_k=10)
    k_hits = _keyword_recall(query, chunks, top_k=10)
    fused = fuse_candidates(v_hits, k_hits, limit=20)
    hybrid_ids = [r.chunk.id for r in fused[:k]]

    # 3. Hybrid + rerank
    reranker = CrossEncoderReranker()
    reranked = reranker.rerank(query, fused, top_k=k)
    rerank_ids = [r.chunk.id for r in reranked]

    return {
        "vector_only": {
            "ids": vec_ids,
            "precision@k": precision_at_k(vec_ids, relevant_ids, k),
        },
        "hybrid": {
            "ids": hybrid_ids,
            "precision@k": precision_at_k(hybrid_ids, relevant_ids, k),
        },
        "hybrid_rerank": {
            "ids": rerank_ids,
            "precision@k": precision_at_k(rerank_ids, relevant_ids, k),
        },
    }
