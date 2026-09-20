"""FastAPI endpoint for Day 5 RAG pipeline.

Kept as a standalone demo app. The retrieval and grounding logic lives in
`app.rag.service` so this endpoint and the main `/ask` endpoint share one
implementation. This one stays offline: it echoes a mock answer instead of
calling a provider.
"""

from fastapi import FastAPI, HTTPException

from app.rag.schemas import AskRequest, RetrievalResponse
from app.rag.service import retrieve, sources_out

app = FastAPI(title="Day 5 RAG API")


@app.post("/ask", response_model=RetrievalResponse)
def ask_endpoint(request: AskRequest) -> RetrievalResponse:
    """Answer a question using the Day 5 RAG pipeline."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    result = retrieve(request.query, request.recall_k, request.final_k)

    return RetrievalResponse(
        query=result["query"],
        answer=f"Based on the context: {result['context'][:100]}...",
        context=result["context"],
        sources=sources_out(result),
        retrieved_ids=result["retrieved_ids"],
    )
