"""Tests for the file-driven markdown/txt corpus loader."""

from app.rag.corpus_loader import build_chunks, list_source_files, split_sections
from app.rag.embeddings import EmbeddingModel


class _SpyEmbedder:
    """Tracks how many chunks asked for an embedding."""

    def __init__(self) -> None:
        self.calls = 0

    def get_embedding(self, text: str) -> list[float]:
        self.calls += 1
        return [1.0]


def test_split_sections_uses_markdown_headings(tmp_path):
    records = split_sections(
        "# Title\n\n## Alpha\n\nFirst paragraph.\n\nSecond line.\n\n"
        "## Beta\n\nOther content.\n"
    )
    # Headings without body content (the bare "# Title") are skipped.
    assert [r.section for r in records] == ["Alpha", "Beta"]
    assert "First paragraph." in records[0].text
    assert "Second line." in records[0].text  # lines kept within the section


def test_unheaded_text_is_chunked_by_paragraph_window(tmp_path):
    paragraphs = [f"Paragraph number {i} about the topic." for i in range(8)]
    records = split_sections("\n\n".join(paragraphs))
    assert records
    assert all(r.section is None for r in records)
    assert len(records) < len(paragraphs)  # windowing collapsed paragraphs


def test_build_chunks_embeds_every_chunk(tmp_path):
    tmp_path.joinpath("a.md").write_text("# One\n\nContent alpha.\n", encoding="utf-8")
    tmp_path.joinpath("b.txt").write_text("# Two\n\nContent beta.\n", encoding="utf-8")
    embedder = _SpyEmbedder()
    chunks = build_chunks(embedder, root=tmp_path)

    assert len(chunks) == 2
    assert {c.id for c in chunks} == {"a-001", "b-001"}
    assert {c.metadata.source for c in chunks} == {"a.md", "b.txt"}
    assert embedder.calls == 2
    assert all(c.metadata.page is None for c in chunks)


def test_build_chunks_dedupes_identical_documents(tmp_path):
    content = "# Handbook\n\nDuplicate body text.\n"
    tmp_path.joinpath("handbook_a.md").write_text(content, encoding="utf-8")
    tmp_path.joinpath("handbook_b.md").write_text(content, encoding="utf-8")
    chunks = build_chunks(_SpyEmbedder(), root=tmp_path)
    assert len(chunks) == 1  # byte-identical docs ingested once


def test_knowledge_base_accepts_only_md_and_txt(tmp_path):
    tmp_path.joinpath("notes.md").write_text("# Notes\n\nBody.\n", encoding="utf-8")
    tmp_path.joinpath("report.pdf").write_bytes(b"%PDF-1.4 fake")
    tmp_path.joinpath("letter.docx").write_bytes(b"PK\x03\x04 fake")
    files = list_source_files(tmp_path)
    assert [f.name for f in files] == ["notes.md"]


def test_default_corpus_is_loadable():
    """The repository corpus dir must resolve to readable chunks."""
    chunks = build_chunks(EmbeddingModel())
    sources = {c.metadata.source for c in chunks}
    assert len(chunks) > 20
    assert "shipping_policy.md" in sources
    assert "account_guide.md" in sources


def test_corpus_preserves_technical_underscores(tmp_path):
    """Tokens like ERR_PAYMENT_403 must survive markdown cleanup."""
    tmp_path.joinpath("errors.md").write_text(
        "# Errors\n\n## Payment\n\nError code ERR_PAYMENT_403 is forbidden.\n",
        encoding="utf-8",
    )
    chunks = build_chunks(_SpyEmbedder(), root=tmp_path)
    assert "ERR_PAYMENT_403" in chunks[0].text


def test_split_sections_ignores_horizontal_rules(tmp_path):
    records = split_sections("# A\n\nbody\n\n---\n\n## B\n\nmore\n")
    assert [r.section for r in records] == ["A", "B"]
    assert all("---" not in r.text for r in records)
