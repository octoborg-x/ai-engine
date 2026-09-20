"""Tests for Week 2 Day 5: BM25 scorer + candidate recall fusion."""

from app.week2.day5.bm25 import BM25
from app.week2.day5.models import Chunk, ChunkMetadata, SearchResult
from app.week2.day5.recall import fuse_candidates

# ---------- BM25 ----------


def test_bm25_term_frequency_saturation():
    """A doc with the term 5x beats a doc with it 1x."""
    bm25 = BM25()
    bm25.fit(
        [
            "refund policy refund refund refund refund",  # f=5
            "refund",  # f=1
            "unrelated document about shipping",
        ]
    )
    scores = [bm25.score("refund", i) for i in range(3)]
    assert scores[0] > scores[1] > scores[2] == 0.0


def test_bm25_rare_term_beats_common_term():
    """A query term that appears in only 1 doc scores higher than one in all docs."""
    bm25 = BM25()
    # "zebra" appears once (rare), "the" appears in all 3 (common)
    bm25.fit(
        [
            "the zebra runs",
            "the cat sleeps",
            "the dog barks",
        ]
    )
    rare = bm25.score("zebra", 0)
    common = bm25.score("the", 0)
    assert rare > common


def test_bm25_length_normalization():
    """With equal TF, the shorter doc scores higher (length norm)."""
    bm25 = BM25()
    bm25.fit(
        [
            "refund " + "filler " * 50,  # long doc, f=1
            "refund",  # short doc, f=1
        ]
    )
    assert bm25.score("refund", 1) > bm25.score("refund", 0)


def test_bm25_top_k_returns_sorted_pairs():
    """Verify that top_k returns results sorted by score in descending order."""
    bm25 = BM25()
    bm25.fit(["alpha beta", "alpha alpha alpha", "gamma"])
    hits = bm25.top_k("alpha", k=2)
    assert len(hits) == 2
    assert hits[0][1] >= hits[1][1]  # sorted desc
    assert hits[0][0] == 1  # doc 1 has TF=3


# ---------- Recall fusion ----------


def _make_result(chunk_id: str, score: float, search_type: str) -> SearchResult:
    chunk = Chunk(
        id=chunk_id,
        text=f"text {chunk_id}",
        metadata=ChunkMetadata(
            document_id="d1",
            source="s.pdf",
            tenant_id="t1",
            created_at="2026-09-01",
        ),
    )
    return SearchResult(chunk=chunk, score=score, search_type=search_type)


def test_fuse_dedupes_by_chunk_id():
    """Same chunk from both channels appears once, tagged 'both', max score kept."""
    vector_hits = [_make_result("a", 0.9, "vector"), _make_result("b", 0.8, "vector")]
    keyword_hits = [
        _make_result("a", 0.7, "keyword"),
        _make_result("c", 0.6, "keyword"),
    ]

    fused = fuse_candidates(vector_hits, keyword_hits, limit=10)
    ids = [r.chunk.id for r in fused]

    assert ids.count("a") == 1
    a = next(r for r in fused if r.chunk.id == "a")
    assert a.search_type == "both"
    assert a.score == 0.9  # max of the two


def test_fuse_respects_limit():
    """Verify that the fusion function respects the max candidate limit."""
    v = [_make_result(str(i), 1.0 - i * 0.01, "vector") for i in range(10)]
    k = [_make_result(str(100 + i), 0.5, "keyword") for i in range(10)]
    assert len(fuse_candidates(v, k, limit=5)) == 5
