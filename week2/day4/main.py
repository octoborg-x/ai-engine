"""
Main entry point for the Day 4 RAG demo.
Demonstrates retrieval, hybrid search, and context building.
"""

# pylint: disable=import-error
from context_builder import build_context
from embeddings import EmbeddingModel
from models import Chunk, ChunkMetadata
from retriever import Retriever
from vector_store import SimpleVectorStore


def run_demo():
    """Initializes components and runs a sample retrieval query."""
    # Initialize components
    embedder = EmbeddingModel()
    store = SimpleVectorStore()
    retriever = Retriever(store, embedder)

    # Seed data with specific metadata
    sample_chunks = [
        Chunk(
            id="1",
            text="Refunds are allowed within 30 days of purchase.",
            metadata=ChunkMetadata(
                document_id="doc_123",
                source="refund-policy.pdf",
                page=1,
                section="Returns",
                tenant_id="company_42",
                created_at="2026-09-01",
            ),
            embedding=embedder.get_embedding(
                "Refunds are allowed within 30 days of purchase."
            ),
        ),
        Chunk(
            id="2",
            text=(
                "Damaged products can be returned if reported within 48 hours. "
                "Error code ERR_PAYMENT_403 indicates a forbidden transaction."
            ),
            metadata=ChunkMetadata(
                document_id="doc_456",
                source="returns.pdf",
                page=2,
                section="Damaged Goods",
                tenant_id="company_42",
                created_at="2026-09-02",
            ),
            embedding=embedder.get_embedding(
                "Damaged products can be returned. Error code ERR_PAYMENT_403"
            ),
        ),
    ]
    store.add_chunks(sample_chunks)

    # User Question
    default_query = "What is the error code ERR_PAYMENT_403?"
    user_query = input(
        f"Enter your question (Press Enter for default: '{default_query}'): "
    ).strip()
    if not user_query:
        user_query = default_query
    print(f"\nUser Question: {user_query}\n")

    # 1. Retrieve (includes Hybrid Search and Metadata filtering)
    results = retriever.retrieve(query=user_query, tenant_id="company_42", top_k=2)

    # 2. Build Context
    formatted_context = build_context(
        retrieved_results=results, max_chunks=2, token_budget=500
    )

    print("--- Formatted Context ---")
    print(formatted_context)
    print("-------------------------")

    # Note: LLM Generation would follow here.


if __name__ == "__main__":
    run_demo()
