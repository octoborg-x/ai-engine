"""
Second-stage reranker.

Re-scores fused candidates by modeling query–chunk interaction.
Two strategies provided:
  1. `CrossEncoderReranker` — learns a scoring function from labeled pairs.
     Stand-in for production cross-encoders (e.g. Cohere Rerank, BGE, ColBERT).
  2. `LLMReranker` — uses an LLM to grade each candidate (production option).

Both expose the same interface: rerank(query, candidates) -> ranked list.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import SearchResult


# pylint: disable=too-few-public-methods
class Reranker(ABC):
    """Interface for second-stage rerankers."""

    @abstractmethod
    def rerank(
        self, query: str, candidates: list[SearchResult], top_k: int
    ) -> list[SearchResult]:
        """Return the top-k candidates re-scored and re-sorted."""


# pylint: disable=too-few-public-methods
class CrossEncoderReranker(Reranker):
    """
    Hand-rolled cross-encoder style reranker.

    A real cross-encoder feeds [query, chunk] jointly through a transformer
    and outputs a single relevance logit. We simulate the *mechanism* with
    a weighted feature model you can train later:

        score = w1 * first_stage_score
              + w2 * lexical_overlap
              + w3 * token_coverage
              + w4 * length_penalty

    The point: reranking uses features the first stage cannot, because it
    sees query and chunk together.
    """

    def __init__(
        self,
        w1: float = 0.3,
        w2: float = 0.3,
        w3: float = 0.25,
        w4: float = 0.15,
    ):
        self.w1 = w1  # trust first-stage score somewhat
        self.w2 = w2  # exact lexical overlap (BM25-like signal, but on the pair)
        self.w3 = w3  # fraction of query tokens present in chunk
        self.w4 = w4  # prefer chunks that are focused, not bloated

    def _lexical_overlap(self, query: str, text: str) -> float:
        q = set(query.lower().split())
        t = set(text.lower().split())
        return len(q & t) / len(q) if q else 0.0

    def _token_coverage(self, query: str, text: str) -> float:
        """Fraction of query tokens that appear in the chunk."""
        q = query.lower().split()
        t = text.lower()
        if not q:
            return 0.0
        hits = sum(1 for tok in q if tok in t)
        return hits / len(q)

    def _length_penalty(self, text: str) -> float:
        """Shorter, focused chunks score higher (normalized to 0-1)."""
        words = len(text.split())
        # Sweet spot ~50-150 words; decays beyond that
        if words <= 150:
            return 1.0
        return max(0.0, 1.0 - (words - 150) / 300)

    def rerank(
        self, query: str, candidates: list[SearchResult], top_k: int
    ) -> list[SearchResult]:
        scored = []
        for c in candidates:
            text = c.chunk.text
            score = (
                self.w1 * c.score
                + self.w2 * self._lexical_overlap(query, text)
                + self.w3 * self._token_coverage(query, text)
                + self.w4 * self._length_penalty(text)
            )
            scored.append(
                SearchResult(chunk=c.chunk, score=score, search_type="reranked")
            )
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]


# pylint: disable=too-few-public-methods
class LLMReranker(Reranker):
    """
    LLM-based reranker: asks the model to grade each candidate 0-10.

    Production-grade rerankers (Cohere Rerank, Voyage, OpenAI, etc.) do this
    with a single batched call. We keep it as an interface so you can swap in
    a real provider later.
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client  # Week 1 LLMClient goes here

    def rerank(
        self, query: str, candidates: list[SearchResult], top_k: int
    ) -> list[SearchResult]:
        if self.llm_client is None:
            raise ValueError("LLMReranker requires an llm_client")
        # pylint: disable=fixme
        # TODO in Step 4: wire to real LLM
        raise NotImplementedError("Wire to LLMClient")
