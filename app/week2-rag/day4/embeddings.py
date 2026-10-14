"""
Embedding model utilities for generating vector representations of text.
"""

import os
import random

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


def default_embedding_model() -> str:
    """Resolve the embedding model, letting OPENAI_MODEL override the default."""
    return os.getenv("OPENAI_MODEL", DEFAULT_EMBEDDING_MODEL)


class EmbeddingModel:
    """
    A mock embedding model wrapper.

    In a production environment, this would interface with a real provider.
    """

    # pylint: disable=too-few-public-methods
    def __init__(self, model_name: str | None = None):
        model_name = model_name or default_embedding_model()
        self.model_name = model_name
        self.dimension = 1536

    def get_embedding(self, _text: str) -> list[float]:
        """Generates a mock embedding vector for the given text."""
        # Mock embedding: In a real app, call OpenAI/Cohere/HuggingFace
        return [random.uniform(-1, 1) for _ in range(self.dimension)]
