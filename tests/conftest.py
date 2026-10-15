"""Pytest configuration for the application package."""

import os
import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest


class _FakeCompletions:
    """Deterministic completion stub so endpoint tests never hit a provider."""

    async def create(self, **kwargs):  # noqa: ARG001
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
        )


class _FakeLLMClient:
    """Minimal stand-in for the lazy OpenAI-compatible client."""

    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions())


@pytest.fixture(autouse=True)
def isolate_external_calls(monkeypatch):
    """Keep the test suite hermetic: no LLM or embedding API calls.

    Tests that exercise the RAG /ask path run the keyword recall offline with
    deterministic zero-vector embeddings, and endpoint-level tests that trigger
    the LLM client get a canned completion instead of a real provider call.
    """
    os.environ["EMBEDDINGS_OFFLINE"] = "1"

    from app.llm import client as llm_client

    monkeypatch.setattr(llm_client, "_client", _FakeLLMClient())
    yield
