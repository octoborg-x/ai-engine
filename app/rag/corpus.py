"""Canonical evaluation corpus, loaded from readable .md/.txt source files.

The corpus is built from the source documents under ``corpus/source_docs``
(override with the ``CORPUS_DIR`` environment variable). Only plain-text
markdown/text files are ingested: no PDF/DOCX parsers are needed. Adding a
knowledge document is as simple as dropping an ``.md`` or ``.txt`` file into
the corpus directory and restarting the service.
"""

from __future__ import annotations

from .corpus_loader import build_chunks, list_source_files
from .embeddings import EmbeddingModel


def build_corpus(embedder: EmbeddingModel) -> list:
    """Build the canonical corpus from the local source files."""
    return build_chunks(embedder)


__all__ = ["build_corpus", "list_source_files"]
