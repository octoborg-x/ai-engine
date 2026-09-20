"""Request/response contracts for the Knowledge Assistant `/ask` endpoint."""

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Question to answer from retrieved knowledge-base context."""

    query: str
    recall_k: int = Field(default=10, ge=1, le=50)
    final_k: int = Field(default=3, ge=1, le=10)


class SourceOut(BaseModel):
    """A retrieved chunk the answer is grounded in."""

    source_id: str
    chunk_id: str
    source: str
    page: int | None = None
    section: str | None = None
    score: float


class RetrievalResponse(BaseModel):
    """Retrieved context and sources, without an LLM answer."""

    query: str
    answer: str
    context: str
    sources: list[SourceOut]
    retrieved_ids: list[str]


class AskResponse(RetrievalResponse):
    """Grounded answer plus the model metadata that produced it."""

    model: str
    route: str
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: float
    latency_ms: float
    citations: dict
