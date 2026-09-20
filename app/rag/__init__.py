"""Shared RAG retrieval and grounding layer for the Knowledge Assistant."""

from app.rag.schemas import (
    AskRequest,
    AskResponse,
    RetrievalResponse,
    SourceOut,
)
from app.rag.service import answer, retrieve, sources_out

__all__ = [
    "AskRequest",
    "AskResponse",
    "RetrievalResponse",
    "SourceOut",
    "answer",
    "retrieve",
    "sources_out",
]
