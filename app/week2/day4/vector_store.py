"""
In-memory vector store implementation with hybrid search capabilities.
"""

from typing import List

import numpy as np

# pylint: disable=import-error
from models import Chunk, SearchResult


class SimpleVectorStore:
    """Simple in-memory vector store for document chunks."""

    def __init__(self):
        self.chunks: List[Chunk] = []

    def add_chunks(self, chunks: List[Chunk]):
        """Add a list of document chunks to the store."""
        self.chunks.extend(chunks)

    def _cosine_similarity(self, v1, v2):
        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        return dot_product / (norm_v1 * norm_v2) if norm_v1 > 0 and norm_v2 > 0 else 0

    def search(
        self,
        query_text: str,
        query_vector: List[float],
        tenant_id: str,
        top_k: int = 5,
        alpha: float = 0.5,
    ) -> List[SearchResult]:
        """Perform hybrid search using vector similarity and keyword matching."""
        results = []

        # Filter by tenant_id first (Metadata Filtering)
        filtered_chunks = [c for c in self.chunks if c.metadata.tenant_id == tenant_id]

        for chunk in filtered_chunks:
            # 1. Vector Similarity (Semantic)
            vector_score = self._cosine_similarity(query_vector, chunk.embedding)

            # 2. Keyword Match (Simple exact term match for demo)
            # In production, use BM25 or a dedicated engine
            query_terms = set(query_text.lower().split())
            text_terms = set(chunk.text.lower().split())
            common_terms = query_terms.intersection(text_terms)
            keyword_score = len(common_terms) / len(query_terms) if query_terms else 0

            # 3. Hybrid Score (Weighted average)
            hybrid_score = (alpha * vector_score) + ((1 - alpha) * keyword_score)

            results.append(
                SearchResult(chunk=chunk, score=hybrid_score, search_type="hybrid")
            )

        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
