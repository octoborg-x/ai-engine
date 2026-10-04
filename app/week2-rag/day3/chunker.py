"""
Demonstration script for chunking and embedding operations.
"""

import os

# pylint: disable=import-error
from embeddings import generate_embedding
from models import Chunk

text_content = "Customers can request a refund within 30 days."
real_embedding = (
    generate_embedding(text_content)
    if os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    else [0.0] * 1536
)

# This file now acts as a demonstration of the individual components
chunk = Chunk(
    id="doc1_chunk_001",
    text=text_content,
    embedding=real_embedding,
    metadata={"document_id": "refund_policy", "page": 3, "section": "Refunds"},
)
