"""
Data models for document chunks, metadata, and search results.
"""

from pydantic import BaseModel


class ChunkMetadata(BaseModel):
    """Metadata for a specific document chunk."""

    document_id: str
    source: str
    page: int | None = None
    section: str | None = None
    tenant_id: str
    created_at: str  # Using string for simplicity, e.g., "2026-09-01"


class Chunk(BaseModel):
    """Represents a piece of text with its associated metadata and embedding."""

    id: str
    text: str
    metadata: ChunkMetadata
    embedding: list[float] | None = None
    score: float = 0.0  # Used for ranking


class SearchResult(BaseModel):
    """A ranked search result containing a chunk and its relevance score."""

    chunk: Chunk
    score: float
    search_type: str  # "vector", "keyword", or "hybrid"
