# pylint: disable=import-error
"""FastAPI endpoint for Day 5 RAG pipeline."""

from embeddings import EmbeddingModel  # Day 4 mock
from fastapi import FastAPI, HTTPException
from models import Chunk, ChunkMetadata
from pipeline import Day5RAGPipeline
from pydantic import BaseModel

app = FastAPI(title="Day 5 RAG API")


class AskRequest(BaseModel):
    """Request body for /ask."""

    query: str
    recall_k: int = 10
    final_k: int = 3


class AskResponse(BaseModel):
    """Response from /ask."""

    query: str
    answer: str  # LLM answer would go here
    context: str
    sources: list[dict]
    retrieved_ids: list[str]


# Initialize with sample data (same pattern as Day 4)
def _seed_pipeline() -> Day5RAGPipeline:
    """Create a pipeline with sample chunks."""
    embedder = EmbeddingModel()
    chunks = [
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
            embedding=embedder.get_embedding("Refunds are allowed within 30 days."),
        ),
        Chunk(
            id="2",
            text="Error code ERR_PAYMENT_403 indicates a forbidden transaction.",
            metadata=ChunkMetadata(
                document_id="doc_456",
                source="errors.pdf",
                page=2,
                section="Payment Errors",
                tenant_id="company_42",
                created_at="2026-09-02",
            ),
            embedding=embedder.get_embedding("Error code ERR_PAYMENT_403 forbidden."),
        ),
    ]
    return Day5RAGPipeline(chunks, embedder)


pipeline = _seed_pipeline()


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(request: AskRequest) -> AskResponse:
    """Answer a question using the Day 5 RAG pipeline."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    result = pipeline.ask(
        query=request.query,
        recall_k=request.recall_k,
        final_k=request.final_k,
    )

    # pylint: disable=fixme
    # TODO: Call real LLM here with result["context"]
    mock_answer = f"Based on the context: {result['context'][:100]}..."

    return AskResponse(
        query=result["query"],
        answer=mock_answer,
        context=result["context"],
        sources=[
            {
                "source_id": s.source_id,
                "chunk_id": s.chunk_id,
                "source": s.source,
                "page": s.page,
            }
            for s in result["sources"]
        ],
        retrieved_ids=result["retrieved_ids"],
    )
