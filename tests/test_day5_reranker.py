"""Tests for Week 2 Day 5 reranker."""

import pytest

from app.week2.day5.models import Chunk, ChunkMetadata, SearchResult
from app.week2.day5.reranker import CrossEncoderReranker, LLMReranker


def _mk(chunk_id: str, text: str, score: float) -> SearchResult:
    chunk = Chunk(
        id=chunk_id,
        text=text,
        metadata=ChunkMetadata(
            document_id="d1", source="s.pdf", tenant_id="t1", created_at="2026-09-01"
        ),
    )
    return SearchResult(chunk=chunk, score=score, search_type="hybrid")


def test_reranker_prefers_high_coverage():
    """Chunk containing all query tokens should beat one with partial coverage,
    even if the partial one had a higher first-stage score."""
    query = "refund policy within 30 days"
    full = _mk(
        "full", "Our refund policy allows returns within 30 days of purchase.", 0.60
    )
    partial = _mk("partial", "We have a policy. It was updated 30 days ago.", 0.95)

    r = CrossEncoderReranker()
    ranked = r.rerank(query, [partial, full], top_k=2)

    assert ranked[0].chunk.id == "full"
    assert ranked[0].search_type == "reranked"


def test_reranker_penalizes_bloated_chunks():
    """At equal coverage, a focused chunk beats a 500-word bloated one."""
    query = "error code ERR_PAYMENT_403"
    focused = _mk(
        "focused", "Error code ERR_PAYMENT_403 means forbidden transaction.", 0.80
    )
    bloated = _mk(
        "bloated", ("Error code ERR_PAYMENT_403. " + "lorem ipsum " * 60), 0.80
    )

    r = CrossEncoderReranker()
    ranked = r.rerank(query, [bloated, focused], top_k=2)

    assert ranked[0].chunk.id == "focused"


def test_reranker_respects_top_k():
    """Verify that the reranker returns exactly top_k candidates."""
    cands = [_mk(str(i), f"token{i}", 1.0 - i * 0.05) for i in range(10)]
    r = CrossEncoderReranker()
    assert len(r.rerank("token3", cands, top_k=3)) == 3


def test_llm_reranker_requires_client():
    """Verify that LLMReranker raises ValueError if no llm_client is provided."""
    with pytest.raises(ValueError):
        LLMReranker().rerank("q", [], top_k=1)
