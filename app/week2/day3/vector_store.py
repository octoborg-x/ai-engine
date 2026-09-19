"""
Vector store implementation for document chunk management.
"""

# pylint: disable=import-error
from models import Chunk


class VectorStore:
    """Simple in-memory store for document chunks."""

    def __init__(self):
        self.chunks: list[Chunk] = []

    def add_chunk(self, chunk: Chunk):
        """Add a chunk to the internal list."""
        self.chunks.append(chunk)

    def get_all_chunks(self) -> list[Chunk]:
        """Retrieve all chunks from the store."""
        return self.chunks
