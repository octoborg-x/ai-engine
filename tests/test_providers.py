"""Tests for unified provider configuration: key + base URL + models per provider."""

from app.llm import providers


def _clear_keys(monkeypatch):
    for key in (
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "LLM_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)


def _clear_all(monkeypatch):
    _clear_keys(monkeypatch)
    for var in (
        "OPENROUTER_BASE_URL",
        "OPENROUTER_MODEL",
        "OPENROUTER_EMBEDDING_MODEL",
        "OPENAI_BASE_URL",
        "OPENAI_MODEL",
        "OPENAI_EMBEDDING_MODEL",
        "GEMINI_BASE_URL",
        "GEMINI_MODEL",
        "GEMINI_EMBEDDING_MODEL",
        "LLM_BASE_URL",
        "LLM_MODEL",
        "MODEL_NAME",
    ):
        monkeypatch.delenv(var, raising=False)


def test_precedence_openrouter_over_openai_over_gemini(monkeypatch):
    _clear_all(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "gem-key")
    monkeypatch.setenv("OPENAI_API_KEY", "oa-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    p = providers.resolve_provider()
    assert p.name == "openrouter"
    assert p.api_key == "or-key"
    assert p.chat_model == "gpt-4o-mini"
    assert p.embedding_model == "openai/text-embedding-3-small"


def test_openai_selected_when_openrouter_absent(monkeypatch):
    _clear_all(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "gem-key")
    monkeypatch.setenv("OPENAI_API_KEY", "oa-key")
    p = providers.resolve_provider()
    assert p.name == "openai"
    assert p.api_key == "oa-key"
    assert p.base_url == "https://api.openai.com/v1"
    assert p.chat_model == "gpt-4o-mini"
    assert p.embedding_model == "text-embedding-3-small"


def test_gemini_selected_when_nothing_else(monkeypatch):
    _clear_all(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "gem-key")
    monkeypatch.setenv(
        "LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai"
    )
    p = providers.resolve_provider()
    assert p.name == "gemini"
    assert p.api_key == "gem-key"
    assert p.chat_model == "gpt-4o-mini"
    assert p.embedding_model == "text-embedding-004"


def test_llm_api_key_aliases_gemini(monkeypatch):
    _clear_all(monkeypatch)
    monkeypatch.setenv("LLM_API_KEY", "generic-key")
    p = providers.resolve_provider()
    assert p.name == "gemini"
    assert p.api_key == "generic-key"
    assert p.base_url == "https://generativelanguage.googleapis.com/v1beta/openai"


def test_llm_base_url_does_not_leak_into_openrouter_or_openai(monkeypatch):
    _clear_all(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    monkeypatch.setenv("GEMINI_API_KEY", "gem-key")
    monkeypatch.setenv(
        "LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai"
    )
    # OpenRouter is active and LLM_BASE_URL (Gemini) must not override it.
    p = providers.resolve_provider()
    assert p.name == "openrouter"
    assert p.base_url == "https://openrouter.ai/api/v1"

    _clear_keys(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "oa-key")
    p = providers.resolve_provider()
    assert p.name == "openai"
    assert p.base_url == "https://api.openai.com/v1"


def test_forced_provider_uses_its_own_key(monkeypatch):
    _clear_all(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    monkeypatch.setenv("OPENAI_API_KEY", "oa-key")
    p = providers.resolve_provider(forced="openai")
    assert p.name == "openai"
    assert p.api_key == "oa-key"


def test_force_unknown_provider_raises(monkeypatch):
    _clear_all(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    try:
        providers.resolve_provider(forced="anthropic")
    except ValueError:
        return
    raise AssertionError("expected ValueError for unknown forced provider")


def test_chat_and_embedding_models_follow_active_provider(monkeypatch):
    _clear_all(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "free/router/model")
    monkeypatch.setenv("GEMINI_MODEL", "gemini/model")
    assert providers.provider_chat_model() == "free/router/model"
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "gem-key")
    assert providers.provider_chat_model() == "gemini/model"


def test_no_config_defaults_to_openai_embedding(monkeypatch):
    _clear_all(monkeypatch)
    assert providers.provider_embedding_model() == "text-embedding-3-small"


def test_has_provider_key_accepts_any_provider(monkeypatch):
    _clear_all(monkeypatch)
    assert not providers.has_provider_key()
    monkeypatch.setenv("GEMINI_API_KEY", "gem-key")
    assert providers.has_provider_key()
