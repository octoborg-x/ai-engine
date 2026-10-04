"""
Candidate recall: fuse vector and keyword retrieval into one deduplicated set.

Architectural rule: recall optimizes for COVERAGE (don't miss anything
plausibly relevant), ranking optimizes for PRECISION. Never conflate them.
"""

from __future__ import annotations

from .models import SearchResult  # reuse the shared chunk/search models


def fuse_candidates(
    vector_hits: list[SearchResult],
    keyword_hits: list[SearchResult],
    limit: int = 20,
) -> list[SearchResult]:
    """
    Union of vector top-k and keyword top-k, deduplicated by chunk id.

    A chunk found by BOTH signals is a strong signal - keep the max score
    and tag it as "both" so the reranker (Step 2) can weight it.
    """
    by_id: dict[str, SearchResult] = {}

    for hit in vector_hits:
        by_id[hit.chunk.id] = hit

    for hit in keyword_hits:
        existing = by_id.get(hit.chunk.id)
        if existing is None:
            by_id[hit.chunk.id] = hit
        else:
            # Found by both channels: keep the higher score, mark dual-match
            best = max(existing.score, hit.score)
            by_id[hit.chunk.id] = SearchResult(
                chunk=hit.chunk, score=best, search_type="both"
            )

    candidates = sorted(by_id.values(), key=lambda r: r.score, reverse=True)
    return candidates[:limit]
