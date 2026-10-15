"""Tests for canonical embedding configuration and offline behavior."""

from app.rag import embeddings


def test_defaults_to_text_embedding_3_small(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    assert embeddings.default_embedding_model() == "text-embedding-3-small"


def test_openai_model_env_overrides_default(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "custom/embed-model")
    assert embeddings.default_embedding_model() == "custom/embed-model"


def test_explicit_model_argument_wins_over_env(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "custom/embed-model")
    assert embeddings.EmbeddingModel("explicit/model").model_name == "explicit/model"


def test_embedding_model_uses_env_when_unspecified(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "custom/embed-model")
    assert embeddings.EmbeddingModel().model_name == "custom/embed-model"


def test_embedding_generation_works_offline(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    vector = embeddings.generate_embedding("offline query")
    assert len(vector) == 1536
    assert set(vector) == {0.0}


def test_embedding_generation_offline_flag_beats_keys(monkeypatch):
    monkeypatch.setenv("EMBEDDINGS_OFFLINE", "1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    monkeypatch.setenv("OPENAI_API_KEY", "oa-key")
    vector = embeddings.generate_embedding("offline forced query")
    assert len(vector) == 1536
    assert set(vector) == {0.0}


def test_embedding_model_is_openrouter_specific_by_default(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    monkeypatch.delenv("OPENROUTER_EMBEDDING_MODEL", raising=False)
    assert embeddings._embedding_model(True) == "openai/text-embedding-3-small"


def test_embedding_model_uses_openai_model_for_fallback_provider(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "custom/embed-model")
    monkeypatch.delenv("OPENAI_EMBEDDING_MODEL", raising=False)
    assert embeddings._embedding_model(False) == "custom/embed-model"


def test_embedding_model_env_overrides_apply_per_provider(monkeypatch):
    monkeypatch.setenv("OPENROUTER_EMBEDDING_MODEL", "vendor/special-embed")
    monkeypatch.setenv("OPENAI_EMBEDDING_MODEL", "fallback/embed")
    assert embeddings._embedding_model(True) == "vendor/special-embed"
    assert embeddings._embedding_model(False) == "fallback/embed"
