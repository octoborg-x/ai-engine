"""
Utilities for formatting retrieved chunks into an LLM context string.
"""

# pylint: disable=import-error
from models import SearchResult


def count_tokens(text: str) -> int:
    """Calculates an approximate token count for the given text."""
    # Mock token count: ~4 characters per token
    return len(text) // 4


def build_context(
    retrieved_results: list[SearchResult], max_chunks: int = 5, token_budget: int = 1000
) -> str:
    """
    Builds a formatted context string from search results.
    Limits by chunk count and token budget.
    """
    selected_chunks = []
    current_tokens = 0

    # 1. Limit the number of chunks initially
    candidate_results = retrieved_results[:max_chunks]

    for res in candidate_results:
        chunk = res.chunk
        metadata = chunk.metadata

        # Format the block
        header = f"[Source: {metadata.source}"
        if metadata.page:
            header += f", Page {metadata.page}"
        header += "]"

        formatted_chunk = f"{header}\n{chunk.text}\n"
        chunk_tokens = count_tokens(formatted_chunk)

        # 2. Check token budget
        if current_tokens + chunk_tokens <= token_budget:
            selected_chunks.append(formatted_chunk)
            current_tokens += chunk_tokens
        else:
            break  # Budget reached

    return "\n".join(selected_chunks)
