"""
Retrieval logic for finding relevant chunks in a vector store.
"""

import numpy as np

# pylint: disable=import-error
from embeddings import generate_embedding
from vector_store import VectorStore


def cosine_similarity(v1, v2):
    """Compute cosine similarity between two numeric vectors."""
    v1 = np.array(v1)
    v2 = np.array(v2)
    if v1.shape != v2.shape:
        return 0.0
    dot = np.dot(v1, v2)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


class Retriever:
    """Handles querying the vector store for similar content."""

    # pylint: disable=too-few-public-methods
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

    def search(self, query: str, top_k: int = 5, metadata_filter: dict | None = None):
        """Perform a similarity search against the vector store with optional filtering."""
        query_embedding = generate_embedding(query)
        chunks = self.vector_store.get_all_chunks()

        scored_results = []
        for chunk in chunks:
            # Apply metadata filtering
            if metadata_filter:
                match = all(
                    chunk.metadata.get(k) == v for k, v in metadata_filter.items()
                )
                if not match:
                    continue

            score = cosine_similarity(query_embedding, chunk.embedding)
            scored_results.append(
                {
                    "id": chunk.id,
                    "text": chunk.text,
                    "score": float(score),
                    "metadata": chunk.metadata,
                }
            )

        # Sort by score descending
        scored_results.sort(key=lambda x: x["score"], reverse=True)
        return scored_results[:top_k]
