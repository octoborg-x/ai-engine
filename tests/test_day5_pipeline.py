# pylint: disable=import-error,wrong-import-position
"""Tests for Week 2 Day 5 full pipeline."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "week2" / "day5"))
sys.path.insert(0, str(Path(__file__).parent.parent / "week2" / "day4"))

import numpy as np  # noqa: E402
from compare import compare_strategies, precision_at_k  # noqa: E402
from models import Chunk, ChunkMetadata  # noqa: E402
from pipeline import Day5RAGPipeline  # noqa: E402


class MockEmbedder:
    """Deterministic mock embedder for testing."""

    # pylint: disable=too-few-public-methods

    def get_embedding(self, text: str) -> list[float]:
        """Return a deterministic bag-of-words hash embedding."""
        vec = [0.0] * 10
        for word in text.lower().split():
            vec[hash(word) % 10] += 1.0
        return vec


def _mk(chunk_id: str, text: str, source: str = "test.pdf") -> Chunk:
    """Create a test chunk."""
    return Chunk(
        id=chunk_id,
        text=text,
        metadata=ChunkMetadata(
            document_id="d1",
            source=source,
            tenant_id="t1",
            created_at="2026-09-01",
        ),
        embedding=None,
    )


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = np.dot(v1, v2)
    norm = np.linalg.norm(v1) * np.linalg.norm(v2)
    return dot / norm if norm > 0 else 0.0


def test_pipeline_returns_sources():
    """Pipeline should return context with source tags."""
    chunks = [
        _mk("1", "refund policy allows returns within 30 days"),
        _mk("2", "error code ERR_PAYMENT_403 means forbidden transaction"),
        _mk("3", "shipping takes 5-7 business days"),
    ]
    embedder = MockEmbedder()
    for c in chunks:
        c.embedding = embedder.get_embedding(c.text)

    pipe = Day5RAGPipeline(chunks, embedder)
    result = pipe.ask("what is the refund policy?", recall_k=3, final_k=2)

    assert "query" in result
    assert "context" in result
    assert "[S1]" in result["context"]
    assert len(result["sources"]) == 2


def test_precision_at_k():
    """precision@k should count relevant items in top-k."""
    assert precision_at_k(["1", "2", "3"], {"1", "3"}, k=3) == 2 / 3
    assert precision_at_k(["1", "2", "3"], {"4"}, k=3) == 0.0
    assert precision_at_k([], {"1"}, k=3) == 0.0


def test_compare_strategies_runs():
    """Comparison harness should return all three strategies."""
    chunks = [
        _mk("1", "refund policy 30 days"),
        _mk("2", "payment error forbidden"),
        _mk("3", "shipping information"),
        _mk("4", "return policy refund"),
    ]
    embedder = MockEmbedder()
    for c in chunks:
        c.embedding = embedder.get_embedding(c.text)

    result = compare_strategies(
        query="refund policy",
        relevant_ids={"1", "4"},
        chunks=chunks,
        embedder=embedder,
        k=2,
    )

    assert "vector_only" in result
    assert "hybrid" in result
    assert "hybrid_rerank" in result
    for strategy in result.values():
        assert "ids" in strategy
        assert "precision@k" in strategy
        assert 0.0 <= strategy["precision@k"] <= 1.0
