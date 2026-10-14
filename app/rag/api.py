"""Standalone retrieval-only API for local demos and integration tests."""
from fastapi import FastAPI, HTTPException

from app.rag.schemas import AskRequest, RetrievalResponse
from app.rag.service import retrieve, sources_out

app = FastAPI(title="RAG Retrieval API")


@app.post("/ask", response_model=RetrievalResponse)
def ask_endpoint(request: AskRequest) -> RetrievalResponse:
    """Return retrieved context and sources without invoking an answer LLM."""
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
