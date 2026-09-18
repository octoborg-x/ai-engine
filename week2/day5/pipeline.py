# pylint: disable=import-error
"""Full Day 5 RAG pipeline: recall -> rerank -> cite."""

import numpy as np
from bm25 import BM25
from citations import build_sources, format_context_with_citations, validate_citations
from models import Chunk, SearchResult
from recall import fuse_candidates
from reranker import CrossEncoderReranker


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = np.dot(v1, v2)
    norm = np.linalg.norm(v1) * np.linalg.norm(v2)
    return dot / norm if norm > 0 else 0.0


class Day5RAGPipeline:
    """Two-stage retrieval with citations."""

    def __init__(self, chunks: list[Chunk], embedder):
        self.embedder = embedder
        self.chunks = chunks
        self.bm25 = BM25()
        self.bm25.fit([c.text for c in chunks])
        self.reranker = CrossEncoderReranker()

    def _vector_recall(self, query: str, top_k: int) -> list[SearchResult]:
        """Return top-k chunks by vector similarity."""
        qv = self.embedder.get_embedding(query)
        scored = []
        for c in self.chunks:
            sim = _cosine_similarity(qv, c.embedding)
            scored.append(SearchResult(chunk=c, score=sim, search_type="vector"))
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    def _keyword_recall(self, query: str, top_k: int) -> list[SearchResult]:
        """Return top-k chunks by BM25 score."""
        hits = self.bm25.top_k(query, k=top_k)
        return [
            SearchResult(chunk=self.chunks[i], score=s, search_type="keyword")
            for i, s in hits
        ]

    def ask(self, query: str, recall_k: int = 10, final_k: int = 3) -> dict:
        """Full pipeline: recall -> rerank -> cite."""
        v_hits = self._vector_recall(query, recall_k)
        k_hits = self._keyword_recall(query, recall_k)
        candidates = fuse_candidates(v_hits, k_hits, limit=recall_k * 2)
        reranked = self.reranker.rerank(query, candidates, top_k=final_k)
        sources = build_sources(reranked)
        context = format_context_with_citations(sources)
        return {
            "query": query,
            "context": context,
            "sources": sources,
            "retrieved_ids": [s.chunk_id for s in sources],
        }

    def validate_answer(self, answer: str, sources) -> dict:
        """Check citations in the LLM's answer."""
        return validate_citations(answer, sources)
