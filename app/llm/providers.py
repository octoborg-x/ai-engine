"""Provider resolution shared by the chat and embedding clients.

Precedence is OpenRouter first, then OpenAI, then a generic OpenAI-compatible
endpoint ({LLM_API_KEY} + {LLM_BASE_URL}). Each provider has its own scoped
base URL so a key is never sent to the wrong endpoint:

- OpenRouter key (``OPENROUTER_API_KEY``) always uses ``OPENROUTER_BASE_URL``.
- OpenAI key (``OPENAI_API_KEY``) always uses ``OPENAI_BASE_URL``.
- ``LLM_BASE_URL`` is only applied to the generic ``LLM_API_KEY`` provider.

Keeping the resolution in one place means the LLM client and the RAG embedding
client always agree on which provider and base URL are active.
"""

import os

OPENROUTER_DEFAULT_URL = "https://openrouter.ai/api/v1"
OPENAI_DEFAULT_URL = "https://api.openai.com/v1"


class Provider:
    """A resolved provider: which key to send and where to send it."""

    def __init__(self, name: str, api_key: str, base_url: str) -> None:
        self.name = name
        self.api_key = api_key
        self.base_url = base_url


def load_provider_key(prefix: str) -> str | None:
    """The secret for a provider, read verbatim from the environment."""
    return os.getenv(prefix)


def resolve_provider() -> Provider:
    """Pick the highest-priority configured provider.

    - ``OPENROUTER_API_KEY`` is the primary provider; it always targets
      ``OPENROUTER_BASE_URL`` (default https://openrouter.ai/api/v1).
    - ``OPENAI_API_KEY`` is the fallback; it always targets
      ``OPENAI_BASE_URL`` (default https://api.openai.com/v1). ``_BASE_URL``
      scoping means ``LLM_BASE_URL`` can never hijack the OpenRouter or OpenAI
      keys to a different endpoint.
    - ``LLM_API_KEY`` (+ ``LLM_BASE_URL``) is a generic OpenAI-compatible
      fallback (Gemini, Groq, Hugging Face, ...) when no OpenRouter/OpenAI key
      is set.
    """
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        return Provider(
            "openrouter",
            openrouter_key,
            os.getenv("OPENROUTER_BASE_URL") or OPENROUTER_DEFAULT_URL,
        )

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        return Provider(
            "openai",
            openai_key,
            os.getenv("OPENAI_BASE_URL") or OPENAI_DEFAULT_URL,
        )

    generic_key = os.getenv("LLM_API_KEY")
    if generic_key:
        return Provider(
            "generic",
            generic_key,
            os.getenv("LLM_BASE_URL") or OPENAI_DEFAULT_URL,
        )

    raise RuntimeError(
        "Configure OPENROUTER_API_KEY or OPENAI_API_KEY "
        "(or LLM_API_KEY with LLM_BASE_URL for a generic OpenAI-compatible "
        "endpoint such as Gemini, Groq, or Hugging Face) to run live"
    )


def has_provider_key() -> bool:
    """True when any provider key is configured, for readiness probes."""
    return bool(
        os.getenv("OPENROUTER_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("LLM_API_KEY")
    )
