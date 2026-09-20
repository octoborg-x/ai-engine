"""
Citation tracking and groundedness validation.

Pipeline:
  1. Tag every context chunk with a stable source ID before it enters the prompt.
  2. The LLM answers, ideally citing [S1], [S2], ...
  3. Validate: every citation in the answer must map to a chunk that was
     actually in context. Anything else is a hallucinated citation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import SearchResult


@dataclass
class Source:
    """A retrievable source unit shown to the LLM."""

    source_id: str  # stable tag, e.g. "S1"
    chunk_id: str
    source: str  # filename / URL
    page: int | None
    section: str | None
    text: str


def build_sources(results: list[SearchResult]) -> list[Source]:
    """Assign stable source IDs to reranked results, in rank order."""
    sources = []
    for i, r in enumerate(results, start=1):
        m = r.chunk.metadata
        sources.append(
            Source(
                source_id=f"S{i}",
                chunk_id=r.chunk.id,
                source=m.source,
                page=m.page,
                section=m.section,
                text=r.chunk.text,
            )
        )
    return sources


def format_context_with_citations(sources: list[Source]) -> str:
    """
    Build the context block for the prompt.

    Each chunk is prefixed with its source tag so the LLM can cite it:
        [S1] (refund-policy.pdf, Page 2, Returns)
        Refunds are allowed within 30 days...
    """
    blocks = []
    for s in sources:
        loc = s.source
        if s.page:
            loc += f", Page {s.page}"
        if s.section:
            loc += f", Section: {s.section}"
        blocks.append(f"[{s.source_id}] ({loc})\n{s.text}")
    return "\n\n".join(blocks)


CITATION_PATTERN = re.compile(r"\[S(\d+)\]")


def extract_citations(answer: str) -> list[str]:
    """Pull all [SN] citation tags out of the LLM's answer."""
    return [f"S{n}" for n in CITATION_PATTERN.findall(answer)]


def validate_citations(answer: str, sources: list[Source]) -> dict:
    """
    Check the answer's citations against what was actually in context.

    Returns:
        valid_citations: tags that map to real sources
        hallucinated_citations: tags with no matching source
        coverage: fraction of provided sources the answer used
    """
    cited = set(extract_citations(answer))
    valid_ids = {s.source_id for s in sources}

    valid = sorted(cited & valid_ids)
    hallucinated = sorted(cited - valid_ids)
    coverage = len(cited & valid_ids) / len(valid_ids) if valid_ids else 0.0

    return {
        "valid_citations": valid,
        "hallucinated_citations": hallucinated,
        "coverage": round(coverage, 2),
        "source_map": {
            s.source_id: f"{s.source}" + (f" p.{s.page}" if s.page else "")
            for s in sources
        },
    }
