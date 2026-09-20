"""Tests for Week 2 Day 5 citation tracking."""

from app.week2.day5.citations import (
    build_sources,
    extract_citations,
    format_context_with_citations,
    validate_citations,
)
from app.week2.day5.models import Chunk, ChunkMetadata, SearchResult


def _mk(chunk_id: str, text: str, source: str, page: int | None = None) -> SearchResult:
    """Create a SearchResult for testing."""
    chunk = Chunk(
        id=chunk_id,
        text=text,
        metadata=ChunkMetadata(
            document_id="d1",
            source=source,
            page=page,
            tenant_id="t1",
            created_at="2026-09-01",
        ),
    )
    return SearchResult(chunk=chunk, score=0.9, search_type="reranked")


test_sources = [
    _mk("1", "Refunds allowed within 30 days.", "refund-policy.pdf", page=2),
    _mk("2", "Error ERR_PAYMENT_403 means forbidden.", "errors.pdf", page=5),
]


def test_build_sources_assigns_stable_ids():
    """Source IDs should be S1, S2 in rank order."""
    srcs = build_sources(test_sources)
    assert [s.source_id for s in srcs] == ["S1", "S2"]
    assert srcs[0].source == "refund-policy.pdf"
    assert srcs[1].page == 5


def test_format_context_includes_source_tags():
    """Context should include [S1], [S2] and source locations."""
    srcs = build_sources(test_sources)
    ctx = format_context_with_citations(srcs)
    assert "[S1]" in ctx and "[S2]" in ctx
    assert "refund-policy.pdf, Page 2" in ctx


def test_extract_citations_finds_all_tags():
    """Should extract S1, S2 from answer text."""
    answer = "Per [S1], refunds take 30 days. Also see [S2] for the error code."
    assert extract_citations(answer) == ["S1", "S2"]


def test_validate_citations_flags_hallucination():
    """S9 is not in sources, should be flagged as hallucinated."""
    srcs = build_sources(test_sources)
    answer = "Refunds are 30 days [S1]. The error is forbidden [S9]."
    result = validate_citations(answer, srcs)
    assert result["valid_citations"] == ["S1"]
    assert result["hallucinated_citations"] == ["S9"]
    assert result["coverage"] == 0.5


def test_validate_citations_perfect_grounding():
    """All citations valid, coverage 1.0."""
    srcs = build_sources(test_sources)
    answer = "See [S1] and [S2]."
    result = validate_citations(answer, srcs)
    assert result["hallucinated_citations"] == []
    assert result["coverage"] == 1.0
