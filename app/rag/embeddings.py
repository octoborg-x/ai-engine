"""Embedding provider adapter shared by corpus indexing and query retrieval."""

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


def default_embedding_model() -> str:
    """Resolve the embedding model from the environment."""
    return os.getenv("OPENAI_MODEL", DEFAULT_EMBEDDING_MODEL)


def generate_embedding(text: str, model: str | None = None) -> list[float]:
    """Generate a provider embedding, using a zero vector for offline runs."""
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return [0.0] * 1536
    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL")
        or os.getenv("OPENROUTER_BASE_URL")
        or "https://api.openai.com/v1",
    )
    response = client.embeddings.create(
        input=[text], model=model or default_embedding_model()
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
