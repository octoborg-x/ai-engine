"""Tests for OPENAI_MODEL embedding-model resolution."""

import importlib

from app.week2.day3 import embeddings as day3_embeddings
from app.week2.day4 import embeddings as day4_embeddings
from app.week2.day5 import embeddings as day5_embeddings


def test_defaults_to_text_embedding_3_small(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    for module in (day3_embeddings, day4_embeddings, day5_embeddings):
        assert module.default_embedding_model() == "text-embedding-3-small"


def test_openai_model_env_overrides_default(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "custom/embed-model")
    for module in (day3_embeddings, day4_embeddings, day5_embeddings):
        assert module.default_embedding_model() == "custom/embed-model"


def test_explicit_model_argument_wins_over_env(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "custom/embed-model")
    assert (
        day4_embeddings.EmbeddingModel("explicit/model").model_name == "explicit/model"
    )
    assert (
        day5_embeddings.EmbeddingModel("explicit/model").model_name == "explicit/model"
    )


def test_embedding_model_uses_env_when_unspecified(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "custom/embed-model")
    assert day5_embeddings.EmbeddingModel().model_name == "custom/embed-model"


def test_generate_embedding_passes_resolved_model(monkeypatch):
    """generate_embedding sends the env-resolved model to the provider client."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "custom/embed-model")

    captured = {}

    class _FakeEmbeddings:
        def create(self, input, model):
            captured["model"] = model
            return type(
                "R", (), {"data": [type("D", (), {"embedding": [0.1, 0.2]})()]}
            )()

    monkeypatch.setattr(
        day3_embeddings,
        "client",
        type("C", (), {"embeddings": _FakeEmbeddings()})(),
    )

    vector = day3_embeddings.generate_embedding("hello")

    assert vector == [0.1, 0.2]
    assert captured["model"] == "custom/embed-model"


def test_module_reload_still_reads_env(monkeypatch):
    """Resolution is dynamic, so a reloaded module honours the current env."""
    monkeypatch.setenv("OPENAI_MODEL", "reload/model")
    reloaded = importlib.reload(day5_embeddings)
    assert reloaded.default_embedding_model() == "reload/model"
