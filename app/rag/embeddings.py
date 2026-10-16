"""Embedding provider adapter shared by corpus indexing and query retrieval.

Embeddings come from the same unified provider as the chat model (openrouter
-- openai -- gemini): key, base URL, chat model, and embedding model all
belong to the active provider.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

from app.llm.providers import (
    has_provider_key,
    provider_embedding_model,
    resolve_provider,
)

load_dotenv()


def default_embedding_model() -> str:
    """Resolve the embedding model for the active provider."""
    return provider_embedding_model()


def _offline_mode() -> bool:
    """True when tests/CI force deterministic zero-vector embeddings."""
    return os.getenv("EMBEDDINGS_OFFLINE", "0") == "1"


def generate_embedding(text: str, model: str | None = None) -> list[float]:
    """Generate a provider embedding, using a zero vector for offline runs.

    Provider precedence is OpenRouter first, OpenAI second, Gemini last.
    When neither a real key nor an explicit ``EMBEDDINGS_OFFLINE=1`` flag is
    present, a deterministic zero vector is returned so tests and local demos
    never hit the network. The embedding model is always the active provider's
    own embedding model, so it can never be a chat model from another provider.
    """
    if _offline_mode() or not has_provider_key():
        return [0.0] * 1536
    provider = resolve_provider()
    client = OpenAI(api_key=provider.api_key, base_url=provider.base_url)
    response = client.embeddings.create(
        input=[text],
        model=model or provider.embedding_model,
    )
    return response.data[0].embedding


class EmbeddingModel:
    """Adapter exposing the get_embedding interface used by the RAG pipeline."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or default_embedding_model()
        self.dimension = 1536

    def get_embedding(self, text: str) -> list[float]:
        """Return a provider embedding or a deterministic offline zero vector."""
        return generate_embedding(text, model=self.model_name)
