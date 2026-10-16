"""File-driven corpus loading for the Knowledge Assistant.

Local source files are plain, human-readable ``.md`` and ``.txt`` documents.
PDF/DOCX are intentionally not parsed: the chunker works on text directly, so
the Knowledge Assistant accepts the same easy-to-read formats the operator
can edit. Uploading a document means dropping an ``.md``/``.txt`` file into
the corpus directory (``CORPUS_DIR``, default ``corpus/source_docs``).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from .embeddings import EmbeddingModel
from .models import Chunk, ChunkMetadata

DEFAULT_CORPUS_DIR = "corpus/source_docs"
SUPPORTED_SUFFIXES = (".md", ".markdown", ".txt")
TENANT_ID = "company_42"
CREATED_AT = "2026-09-01"

# Lines that add no retrievable content.
_SKIP_LINE_RE = re.compile(r"^\s*(---|\*\*\*|===|<!--|-->\s*$|$)")
# Inline markup (bold, italic, code spans, links) we can safely strip for text.
_MARKUP_RE = re.compile(r"[`*~]|\[([^\]]*)]\([^)]*\)|\]\([^)]*\)")


@dataclass
class RawRecord:
    """One logical section extracted from a source file."""

    text: str
    section: str | None


def list_source_files(root: str | os.PathLike | None = None) -> list[Path]:
    """Resolve the corpus directory and list supported source files."""
    directory = Path(root or os.getenv("CORPUS_DIR") or DEFAULT_CORPUS_DIR)
    if not directory.is_dir():
        raise FileNotFoundError(
            f"corpus directory not found: {directory} (set CORPUS_DIR to point "
            f"at a folder of .md/.txt files)"
        )
    files = sorted(
        p for p in directory.iterdir() if p.suffix.lower() in SUPPORTED_SUFFIXES
    )
    if not files:
        raise FileNotFoundError(
            f"no .md/.txt files found in {directory}; add readable source "
            f"documents to the corpus"
        )
    return files


def _slugify(stem: str) -> str:
    """Turn a filename stem into a stable id prefix: ``shipping_policy``."""
    stem = stem.strip().lower()
    stem = re.sub(r"[^a-z0-9]+", "_", stem).strip("_")
    return stem or "doc"


def _clean_line(line: str) -> str:
    """Trim markdown noise while keeping the readable text."""
    line = _MARKUP_RE.sub(r"\1" if "[" in line else "", line)
    line = line.replace("**", "").replace("*", "").replace("`", "")
    return line.strip()


def _paragraph_chunks(lines: list[str], group: int = 4, overlap: int = 1) -> list[str]:
    """Group unheaded text into paragraph windows for reasonable chunk sizes."""
    paragraphs = [
        p.strip() for p in re.split(r"\n\s*\n", "\n".join(lines)) if p.strip()
    ]
    if not paragraphs:
        return []
    chunks: list[str] = []
    window = group
    step = max(1, window - overlap)
    for start in range(0, len(paragraphs), step):
        pieces = paragraphs[start : start + window]
        if pieces:
            chunks.append("\n".join(pieces))
    return chunks


def split_sections(
    text: str, fallback_group: int = 4, fallback_overlap: int = 1
) -> list[RawRecord]:
    """Split a document into logical sections using markdown headings.

    Every ``#``-level heading starts a new section; body paragraphs are joined
    under the most recent heading. Documents without headings are chunked by
    paragraph windows so chunks stay focused.
    """
    lines = text.splitlines()
    sections: list[RawRecord] = []
    current: RawRecord | None = None
    for line in lines:
        stripped = line.rstrip()
        heading = re.match(r"^\s{0,3}#{1,6}\s+(.*)$", stripped)
        if heading:
            if current is not None and current.text.strip():
                sections.append(current)
            current = RawRecord(text="", section=heading.group(1).strip())
            continue
        if _SKIP_LINE_RE.match(line):
            continue
        cleaned = _clean_line(line)
        if not cleaned:
            continue
        if current is None:
            current = RawRecord(text="", section=None)
        current.text += cleaned + "\n"

    if current is not None and current.text.strip():
        sections.append(current)

    headed = [s for s in sections if s.section]
    if headed:
        return [RawRecord(text=s.text.strip(), section=s.section) for s in headed]

    plain = [s.text for s in sections if s.text.strip()]
    return [
        RawRecord(text=text, section=None) for text in _paragraph_chunks(plain) if text
    ]


def load_documents(
    root: str | os.PathLike | None = None,
) -> list[tuple[Path, str]]:
    """Read every supported source file in the corpus directory as text."""
    return [
        (path, path.read_text(encoding="utf-8")) for path in list_source_files(root)
    ]


def _normalize_for_dedup(text: str) -> str:
    """Collapse whitespace so identical documents dedupe across filenames."""
    return re.sub(r"\s+", " ", text).strip()


def build_chunks(
    embedder: EmbeddingModel, root: str | os.PathLike | None = None
) -> list[Chunk]:
    """Parse every source file into embedded, source-tagged chunks.

    Byte-identical documents that exist under different filenames are ingested
    once to keep the corpus and the retrieval quality metrics meaningful.
    """
    chunks: list[Chunk] = []
    seen: set[str] = set()
    for path, text in load_documents(root):
        slug = _slugify(path.stem)
        for index, record in enumerate(split_sections(text), start=1):
            key = _normalize_for_dedup(record.text)
            if key in seen:
                continue
            seen.add(key)
            chunks.append(
                Chunk(
                    id=f"{slug}-{index:03d}",
                    text=record.text,
                    metadata=ChunkMetadata(
                        document_id=slug,
                        source=path.name,
                        page=None,
                        section=record.section,
                        tenant_id=TENANT_ID,
                        created_at=CREATED_AT,
                    ),
                    embedding=embedder.get_embedding(record.text),
                )
            )
    return chunks
