"""Production RAG pipeline: hybrid recall, reranking, and citation grounding."""

import numpy as np

from app.rag.bm25 import BM25
from app.rag.citations import (
    build_sources,
    format_context_with_citations,
    validate_citations,
)
from app.rag.models import Chunk, SearchResult
from app.rag.recall import fuse_candidates
from app.rag.reranker import CrossEncoderReranker


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    dot = np.dot(v1, v2)
    norm = np.linalg.norm(v1) * np.linalg.norm(v2)
    return dot / norm if norm > 0 else 0.0


class RAGPipeline:
    """Two-stage hybrid retrieval with grounded source citations."""

    def __init__(self, chunks: list[Chunk], embedder):
        self.embedder = embedder
        self.chunks = chunks
        self.bm25 = BM25()
        self.bm25.fit([c.text for c in chunks])
        self.reranker = CrossEncoderReranker()

    def _vector_recall(self, query: str, top_k: int) -> list[SearchResult]:
        qv = self.embedder.get_embedding(query)
        scored = [
            SearchResult(
                chunk=c,
                score=_cosine_similarity(qv, c.embedding or []),
                search_type="vector",
            )
            for c in self.chunks
        ]
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]

    def _keyword_recall(self, query: str, top_k: int) -> list[SearchResult]:
        return [
            SearchResult(chunk=self.chunks[i], score=score, search_type="keyword")
            for i, score in self.bm25.top_k(query, k=top_k)
        ]

    def ask(self, query: str, recall_k: int = 10, final_k: int = 3) -> dict:
        vector_hits = self._vector_recall(query, recall_k)
        keyword_hits = self._keyword_recall(query, recall_k)
        candidates = fuse_candidates(vector_hits, keyword_hits, limit=recall_k * 2)
        reranked = self.reranker.rerank(query, candidates, top_k=final_k)
        sources = build_sources(reranked)
        rerank_by_id = {result.chunk.id: result.score for result in reranked}
        return {
            "query": query,
            "context": format_context_with_citations(sources),
            "sources": sources,
            "source_scores": [result.score for result in reranked],
            "retrieved_ids": [source.chunk_id for source in sources],
            "candidates": self._describe_candidates(candidates, rerank_by_id),
        }

    @staticmethod
    def _describe_candidates(
        candidates: list[SearchResult], rerank_by_id: dict[str, float]
    ) -> list[dict]:
        """Describe fused candidates with their recall and rerank scores.

        Makes the two-stage retrieval auditable: which chunks were recalled,
        how each was scored, and which ones survived reranking into context.
        """
        described = []
        for candidate in candidates:
            chunk = candidate.chunk
            rerank_score = rerank_by_id.get(chunk.id)
            described.append(
                {
                    "chunk_id": chunk.id,
                    "source": chunk.metadata.source,
                    "page": chunk.metadata.page,
                    "section": chunk.metadata.section,
                    "text": chunk.text,
                    "recall_score": round(candidate.score, 4),
                    "recall_type": candidate.search_type,
                    "rerank_score": (
                        round(rerank_score, 4) if rerank_score is not None else None
                    ),
                    "kept": rerank_score is not None,
                }
            )
        return described

    def validate_answer(self, answer: str, sources) -> dict:
        return validate_citations(answer, sources)
