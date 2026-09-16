"""
Retriever logic for orchestrating search across the vector store.
"""

# pylint: disable=import-error
from embeddings import EmbeddingModel
from models import SearchResult
from vector_store import SimpleVectorStore


class Retriever:
    """Handles the high-level retrieval flow from query to search results."""

    # pylint: disable=too-few-public-methods
    def __init__(
        self, vector_store: SimpleVectorStore, embedding_model: EmbeddingModel
    ):
        """Initializes the retriever with a store and an embedding model."""
        self.vector_store = vector_store
        self.embedding_model = embedding_model

    def retrieve(
        self, query: str, tenant_id: str, top_k: int = 5
    ) -> list[SearchResult]:
        """Embeds the query and performs a hybrid search in the vector store."""
        # 1. Get query embedding
        query_vector = self.embedding_model.get_embedding(query)

        # 2. Perform Hybrid Search
        results = self.vector_store.search(
            query_text=query,
            query_vector=query_vector,
            tenant_id=tenant_id,
            top_k=top_k,
        )
        return results
