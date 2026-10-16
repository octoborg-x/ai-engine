"""Embedding provider adapter shared by corpus indexing and query retrieval."""

import os

from dotenv import load_dotenv
from openai import OpenAI

from app.llm.providers import has_provider_key, resolve_provider

load_dotenv()
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
OPENROUTER_EMBEDDING_MODEL = "openai/text-embedding-3-small"


def default_embedding_model() -> str:
    """Resolve the embedding model from the environment."""
    return os.getenv("OPENAI_MODEL", DEFAULT_EMBEDDING_MODEL)


def _offline_mode() -> bool:
    """True when tests/CI force deterministic zero-vector embeddings."""
    return os.getenv("EMBEDDINGS_OFFLINE", "0") == "1"


def _embedding_model(openrouter: bool) -> str:
    """Pick an embedding-capable model for the active provider.

    `OPENAI_MODEL` is a general-purpose (often chat) model, so OpenRouter
    embeddings default to the OpenRouter-compatible text-embedding model
    unless ``OPENROUTER_EMBEDDING_MODEL`` is set explicitly.
    """
    if openrouter:
        return os.getenv("OPENROUTER_EMBEDDING_MODEL") or OPENROUTER_EMBEDDING_MODEL
    return os.getenv("OPENAI_EMBEDDING_MODEL") or default_embedding_model()


def generate_embedding(text: str, model: str | None = None) -> list[float]:
    """Generate a provider embedding, using a zero vector for offline runs.

    Provider precedence is OpenRouter first, OpenAI (or any OpenAI-compatible
    endpoint such as Gemini) as a fallback. When neither a real key nor an
    explicit ``EMBEDDINGS_OFFLINE=1`` flag is present, a deterministic zero
    vector is returned so tests and local demos never hit the network.
    """
    if _offline_mode() or not has_provider_key():
        return [0.0] * 1536
    provider = resolve_provider()
    base_url = os.getenv("LLM_BASE_URL") or provider.base_url
    client = OpenAI(api_key=provider.api_key, base_url=base_url)
    openrouter = provider.name == "openrouter"
    response = client.embeddings.create(
        input=[text],
        model=model or _embedding_model(openrouter),
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
