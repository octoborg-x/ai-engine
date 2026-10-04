"""
Domain models for the AI application.
"""

from dataclasses import dataclass


@dataclass
class Chunk:
    """Data structure representing a document chunk and its embedding."""

    id: str
    text: str
    embedding: list[float]
    metadata: dict
