"""
Functions for generating text embeddings using external APIs.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
    or os.getenv("OPENROUTER_BASE_URL")
    or "https://api.openai.com/v1",
)


def generate_embedding(text: str, model: str = "text-embedding-3-small") -> list[float]:
    """Generate a real embedding using the OpenAI/OpenRouter client."""
    # Safety check for missing API keys
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        # Return a dummy vector of 1536 dimensions if no key is provided
        return [0.0] * 1536

    response = client.embeddings.create(input=[text], model=model)
    return response.data[0].embedding
