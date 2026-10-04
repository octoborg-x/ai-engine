"""Utility functions for text chunking and paragraph splitting."""

from dataclasses import dataclass


@dataclass
class Chunk:
    """Represents a single chunk of text with metadata."""

    text: str
    chunk_index: int
    source: str


def chunk_text(
    text: str,
    source: str,
    max_words: int = 100,
    overlap: int = 20,
) -> list[Chunk]:
    """Split text into overlapping chunks based on word count."""
    words = text.split()

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(words):
        end = min(start + max_words, len(words))

        chunk_words = words[start:end]

        chunks.append(
            Chunk(
                text=" ".join(chunk_words),
                chunk_index=chunk_index,
                source=source,
            )
        )

        chunk_index += 1

        if end == len(words):
            break

        start = end - overlap

    return chunks


def split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs based on double newlines."""
    return [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
