"""Endpoint tests for the file-driven knowledge base (list/upload/delete).

Uses an isolated corpus/uploads pair so the git-tracked corpus is untouched.
"""

import os

os.environ.setdefault("API_AUTH_TOKEN", "test-auth-token")

import pytest
from fastapi.testclient import TestClient

import app.main as api
from app.security.rate_limit import rate_limiter

auth_headers = {"Authorization": "Bearer test-auth-token"}


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    rate_limiter._hits.clear()
    yield


@pytest.fixture
def corpus_env(tmp_path, monkeypatch):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    corpus.joinpath("policy.md").write_text(
        "# Policy\n\nFollow the policy.\n", encoding="utf-8"
    )
    uploads = tmp_path / "uploads"
    monkeypatch.setenv("CORPUS_DIR", str(corpus))
    monkeypatch.setenv("UPLOAD_DIR", str(uploads))
    client = TestClient(api.app)
    yield client, corpus, uploads


def test_sources_requires_auth(corpus_env):
    client, _, _ = corpus_env
    assert client.get("/rag/sources").status_code == 401


def test_sources_lists_local_and_upload(corpus_env):
    client, _, uploads = corpus_env
    uploads.mkdir()
    uploads.joinpath("added.md").write_text(
        "# Added\n\nNew content.\n", encoding="utf-8"
    )

    response = client.get("/rag/sources", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    names = {s["name"]: s for s in payload["sources"]}
    assert "policy.md" in names
    assert "added.md" in names
    assert names["policy.md"]["kind"] == "local"
    assert names["added.md"]["kind"] == "upload"
    assert ".md" in payload["formats"]


def test_upload_persists_and_reindexes(corpus_env):
    client, _, uploads = corpus_env
    response = client.post(
        "/rag/sources",
        headers=auth_headers,
        files={
            "file": ("warranty.md", b"# Warranty\n\nCovers defects.\n", "text/markdown")
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["name"] == "warranty.md"
    assert (uploads / "warranty.md").exists()

    # The new document is listed right after upload.
    listed = client.get("/rag/sources", headers=auth_headers).json()["sources"]
    assert any(s["name"] == "warranty.md" for s in listed)


def test_upload_rejects_unsupported_format(corpus_env):
    client, _, _ = corpus_env
    response = client.post(
        "/rag/sources",
        headers=auth_headers,
        files={"file": ("report.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert response.status_code == 422
    assert "only .md/.markdown/.txt" in response.json()["detail"]


def test_delete_removes_uploaded_file(corpus_env):
    client, _, uploads = corpus_env
    uploads.mkdir()
    uploads.joinpath("temp.md").write_text("# Temp\n\nDisposable.\n", encoding="utf-8")

    response = client.delete("/rag/sources?name=temp.md", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert not (uploads / "temp.md").exists()


def test_delete_local_source_is_404(corpus_env):
    client, _, _ = corpus_env
    response = client.delete("/rag/sources?name=policy.md", headers=auth_headers)
    assert response.status_code == 404
