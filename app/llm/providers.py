"""Unified provider configuration: one key + base URL + models per provider.

Precedence is OpenRouter first, OpenAI next, then Gemini. Every selected
provider is fully self-contained — its API key, base URL, chat model, and
embedding model all come from the same provider, and a key is never sent to a
different provider's endpoint (the original cause of the Gemini "400 Please
pass a valid API key").

Per-provider variables (``<NAME>`` in ``{OPENROUTER, OPENAI, GEMINI}``):

- ``<NAME>_API_KEY`` — the key (e.g. ``OPENROUTER_API_KEY``).
- ``<NAME>_BASE_URL`` — the endpoint (e.g. ``OPENROUTER_BASE_URL``).
- ``<NAME>_MODEL`` — the chat model (e.g. ``OPENROUTER_MODEL``).
- ``<NAME>_EMBEDDING_MODEL`` — the embedding model (e.g.
  ``OPENROUTER_EMBEDDING_MODEL``).

Legacy aliases still work: ``LLM_API_KEY``/``LLM_BASE_URL`` map to the Gemini
slot (a generic OpenAI-compatible key), and ``MODEL_NAME`` stays the
fallback chat model for every provider.
"""

import os

OPENROUTER_DEFAULT_URL = "https://openrouter.ai/api/v1"
OPENAI_DEFAULT_URL = "https://api.openai.com/v1"
GEMINI_DEFAULT_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
GEMINI_DEFAULT_EMBEDDING_MODEL = "text-embedding-004"
OPENROUTER_EMBEDDING_MODEL_DEFAULT = "openai/text-embedding-3-small"

PROVIDER_ORDER = ("openrouter", "openai", "gemini")

_DEFAULT_URLS = {
    "openrouter": OPENROUTER_DEFAULT_URL,
    "openai": OPENAI_DEFAULT_URL,
    "gemini": GEMINI_DEFAULT_URL,
}


class Provider:
    """A resolved provider with its key, base URL, and models."""

    def __init__(
        self,
        name: str,
        api_key: str,
        base_url: str,
        chat_model: str,
        embedding_model: str,
    ) -> None:
        self.name = name
        self.api_key = api_key
        self.base_url = base_url
        self.chat_model = chat_model
        self.embedding_model = embedding_model


def _env(provider: str, suffix: str) -> str:
    """Provider-scoped env var name, e.g. openrouter + BASE_URL."""
    return f"{provider.upper()}_{suffix}"


def _generic_key() -> str | None:
    """The Gemini-compatible key, honoring the old LLM_API_KEY alias."""
    return os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")


def resolve_provider(forced: str | None = None) -> Provider:
    """Select the highest-priority configured provider (or force one).

    Precedence is openrouter > openai > gemini. A provider is considered
    configured when its API key is present. ``LLM_API_KEY`` (the legacy generic
    slot) is treated as the Gemini key.
    """
    if forced and forced not in PROVIDER_ORDER:
        raise ValueError(f"unknown provider: {forced}")
    if forced:
        return _build_provider(forced)

    for name in PROVIDER_ORDER:
        if name == "gemini":
            if _generic_key():
                return _build_provider("gemini")
            continue
        if os.getenv(_env(name, "API_KEY")):
            return _build_provider(name)

    raise RuntimeError(
        "Configure OPENROUTER_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY "
        "(or LLM_API_KEY with LLM_BASE_URL for a generic OpenAI-compatible "
        "endpoint such as Gemini) to run live"
    )


def _build_provider(name: str) -> Provider:
    """Assemble the full config for one provider from its scoped env vars."""
    api_key = _generic_key() if name == "gemini" else os.getenv(_env(name, "API_KEY"))
    if not api_key:
        raise RuntimeError(f"No API key configured for provider '{name}'")

    base_url = os.getenv(_env(name, "BASE_URL"))
    if name == "gemini" and not base_url:
        base_url = os.getenv("LLM_BASE_URL")
    base_url = (base_url or _DEFAULT_URLS[name]).rstrip("/")

    return Provider(
        name=name,
        api_key=api_key,
        base_url=base_url,
        chat_model=_chat_model(name),
        embedding_model=_provider_embedding_model(name),
    )


def _chat_model(name: str) -> str:
    """The chat model for a provider, defaulting to MODEL_NAME."""
    return os.getenv(_env(name, "MODEL")) or os.getenv("MODEL_NAME", "gpt-4o-mini")


def _provider_embedding_model(name: str) -> str:
    """Embedding model for a provider, honoring per-provider env overrides."""
    if os.getenv(_env(name, "EMBEDDING_MODEL")):
        return os.getenv(_env(name, "EMBEDDING_MODEL"))
    if name == "openrouter":
        return (
            os.getenv("OPENROUTER_EMBEDDING_MODEL")
            or OPENROUTER_EMBEDDING_MODEL_DEFAULT
        )
    if name == "openai":
        return os.getenv("OPENAI_EMBEDDING_MODEL") or os.getenv(
            "OPENAI_MODEL", "text-embedding-3-small"
        )
    return GEMINI_DEFAULT_EMBEDDING_MODEL


def has_provider_key() -> bool:
    """True when any provider key is configured, for readiness probes."""
    return bool(
        os.getenv("OPENROUTER_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("LLM_API_KEY")
    )


def _configured_provider() -> str:
    """Highest-priority provider with a key or model configured.

    Used for model selection (which never calls the network): the chat and
    embedding model should match the provider the operator actually chose via
    ``resolve_provider``'s key precedence, without needing the secret itself.
    Defaults to OpenAI (the last step) when nothing is configured.
    """
    for name in PROVIDER_ORDER:
        if name == "openrouter" and os.getenv(_env(name, "API_KEY")):
            return name
        if name == "openai" and os.getenv(_env(name, "API_KEY")):
            return name
        if name == "gemini" and (
            os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
        ):
            return name
    # No key anywhere: choose by explicit model env, then the default provider.
    for name in PROVIDER_ORDER:
        if os.getenv(_env(name, "MODEL")):
            return name
    return "openai"


def provider_chat_model(provider: str | None = None) -> str:
    """The chat model for the active (or named) provider."""
    if provider:
        return _chat_model(provider)
    return _chat_model(_configured_provider())


def provider_embedding_model(provider: str | None = None) -> str:
    """The embedding model for the active (or named) provider."""
    if provider:
        return _provider_embedding_model(provider)
    return _provider_embedding_model(_configured_provider())
