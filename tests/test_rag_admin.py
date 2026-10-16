"""Tests for the file-driven knowledge base: list, upload, and delete sources."""

import os

import pytest

from app.rag import admin

CORPUS = os.path.join(os.path.dirname(__file__), "..", "corpus", "source_docs")


@pytest.fixture
def isolated_dirs(tmp_path, monkeypatch):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    uploads = tmp_path / "uploads"
    corpus.joinpath("base.md").write_text(
        "# Base\n\nLocal content.\n", encoding="utf-8"
    )
    monkeypatch.setenv("CORPUS_DIR", str(corpus))
    monkeypatch.setenv("UPLOAD_DIR", str(uploads))
    return corpus, uploads


def test_sources_lists_uploads_first_then_local(isolated_dirs):
    corpus, uploads = isolated_dirs
    uploads.mkdir()
    uploads.joinpath("added.md").write_text(
        "# Added\n\nNew content.\n", encoding="utf-8"
    )

    sources = admin.list_sources()
    names = [s.name for s in sources]

    assert "added.md" in names
    assert "base.md" in names
    assert sources[0].kind == "upload"
    assert sources[0].name == "added.md"


def test_save_upload_writes_into_upload_dir(isolated_dirs):
    corpus, uploads = isolated_dirs

    info = admin.save_upload("guide.md", "# Guide\n\nHow to do things.\n")

    assert info.kind == "upload"
    assert (uploads / "guide.md").exists()
    assert info.sections >= 1


def test_save_upload_rejects_non_readable_formats(isolated_dirs):
    with pytest.raises(ValueError, match="only .md/.markdown/.txt"):
        admin.save_upload("notes.docx", "not allowed")


def test_save_upload_rejects_empty_document(isolated_dirs):
    with pytest.raises(ValueError, match="empty"):
        admin.save_upload("empty.md", "   \n\n  ")


def test_save_upload_strips_client_paths(isolated_dirs):
    info = admin.save_upload("../../evil.md", "# Safe\n\nStill saved.\n")
    assert info.name == "evil.md"
    assert (isolated_dirs[1] / "evil.md").exists()


def test_delete_removes_uploaded_file(isolated_dirs):
    admin.save_upload("temp.md", "# Temp\n\nDisposable.\n")
    removed = admin.delete_source("temp.md")
    assert removed is not None
    assert removed.name == "temp.md"
    assert not (isolated_dirs[1] / "temp.md").exists()


def test_delete_never_removes_local_corpus_file(isolated_dirs):
    removed = admin.delete_source("base.md")
    assert removed is None
    assert (isolated_dirs[0] / "base.md").exists()


def test_sources_payload_shape(isolated_dirs):
    payload = admin.sources_payload()
    assert "sources" in payload
    assert ".md" in payload["formats"]
    assert payload["max_upload_bytes"] > 0


def test_merge_uploads_into_corpus(isolated_dirs, monkeypatch):
    """The retrieval corpus sees both local docs and uploaded docs."""
    from app.rag.corpus_loader import load_documents

    corpus, uploads = isolated_dirs
    uploads.mkdir()
    uploads.joinpath("added.md").write_text(
        "# Added\n\nNew content.\n", encoding="utf-8"
    )

    docs = load_documents()
    texts = {path.name: text for path, text in docs}
    assert "added.md" in texts
    assert "base.md" in texts


def test_corpus_dirs_env_follows_config(isolated_dirs):
    assert str(admin.corpus_dir()) == str(isolated_dirs[0])
    assert str(admin.upload_dir()) == str(isolated_dirs[1])
