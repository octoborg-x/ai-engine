"""Knowledge-base file management: list, upload, and delete editable sources.

The knowledge base is plain-text files — ``.md``, ``.markdown``, ``.txt`` — so
the console can show exactly what will be retrieved and extend it without a
database or a PDF/DOCX parser. Files ship in the git-tracked corpus
(``CORPUS_DIR``, default ``corpus/source_docs``) and are listed as ``local``;
files uploaded through the console land in ``UPLOAD_DIR`` (default
``corpus/uploads``) and are listed as ``upload``. No database is involved.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .corpus_loader import (
    DEFAULT_CORPUS_DIR,
    DEFAULT_UPLOAD_DIR,
    SUPPORTED_SUFFIXES,
    split_sections,
)

MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MiB keeps embedding warm-ups focused.


def upload_dir() -> Path:
    """The directory uploaded documents are persisted to."""
    return Path(os.getenv("UPLOAD_DIR") or DEFAULT_UPLOAD_DIR)


def corpus_dir() -> Path:
    """The git-tracked source-documents directory."""
    return Path(os.getenv("CORPUS_DIR") or DEFAULT_CORPUS_DIR)


@dataclass
class SourceInfo:
    """Public shape of one knowledge file shown in the console."""

    name: str
    kind: str  # "local" (git-tracked corpus) or "upload" (console upload)
    size_bytes: int
    modified_at: float
    sections: int


def list_sources() -> list[SourceInfo]:
    """Metadata for every knowledge file, uploaded first, then local."""
    infos: list[SourceInfo] = []
    for directory in (upload_dir(), corpus_dir()):
        if not directory.is_dir():
            continue
        for path in sorted(
            p for p in directory.iterdir() if p.suffix.lower() in SUPPORTED_SUFFIXES
        ):
            infos.append(source_info(path))
    return infos


def save_upload(
    filename: str, content: bytes | str, *, author: str | None = None
) -> SourceInfo:
    """Persist an uploaded document into the upload directory.

    Only ``.md``/``.markdown``/``.txt`` are accepted. Overwrites an existing
    uploaded file with the same name (an upload shadows a local file of the
    same name). The corpus is rebuilt by the caller afterwards.
    """
    name = Path(filename).name  # strip any client-supplied directory parts
    if not name or name in (".", ".."):
        raise ValueError("filename must not be empty")
    suffix = Path(name).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(
            f"unsupported format {suffix or '(none)'}; only .md/.markdown/.txt "
            "documents are accepted"
        )
    if isinstance(content, bytes):
        if len(content) > MAX_UPLOAD_BYTES:
            raise ValueError(
                f"document is too large (max {MAX_UPLOAD_BYTES // 1024} KiB)"
            )
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as e:
            raise ValueError("document must be UTF-8 text") from e
    else:
        text = content
    if not text.strip():
        raise ValueError("document is empty")

    directory = upload_dir()
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / name
    destination.write_text(text, encoding="utf-8")
    return source_info(destination)


def source_info(path: Path) -> SourceInfo:
    """Single source metadata for a knowledge file."""
    kind = "upload" if path.parent.resolve() == upload_dir().resolve() else "local"
    try:
        text = path.read_text(encoding="utf-8")
        sections = len([s for s in split_sections(text) if s.text.strip()])
    except (OSError, UnicodeDecodeError):
        sections = 0
    return SourceInfo(
        name=path.name,
        kind=kind,
        size_bytes=path.stat().st_size,
        modified_at=path.stat().st_mtime,
        sections=sections,
    )


def delete_source(name: str) -> SourceInfo | None:
    """Remove an uploaded document. Local (git-tracked) files are never deleted.

    Returns the removed source metadata, or ``None`` if no uploaded file with
    that name existed.
    """
    directory = upload_dir()
    target = directory / Path(name).name
    if target.parent != directory or not directory.is_dir() or not target.is_file():
        return None
    removed = source_info(target)
    target.unlink()
    return removed


def sources_payload() -> dict:
    """The payload for ``GET /rag/sources`` (local + uploaded files)."""
    sources = list_sources()
    return {
        "sources": [
            {
                "name": s.name,
                "kind": s.kind,
                "size_bytes": s.size_bytes,
                "modified_at": s.modified_at,
                "sections": s.sections,
            }
            for s in sources
        ],
        "formats": list(SUPPORTED_SUFFIXES),
        "max_upload_bytes": MAX_UPLOAD_BYTES,
    }
