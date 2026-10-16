import json
import os
from types import SimpleNamespace

os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("MODEL_NAME", "cohere/north-mini-code:free")

import pytest
from openai import APIError, APITimeoutError, RateLimitError
from tenacity import wait_none

from app.llm import client as llm_client


def completion_response(content, prompt_tokens=10, completion_tokens=5):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
        ),
    )


@pytest.mark.parametrize(
    ("or_key", "oa_key", "expected_key", "expected_url"),
    [
        # OpenRouter is the primary provider when both are configured.
        ("or-key", "oa-key", "or-key", "https://openrouter.ai/api/v1"),
        # OpenAI is used only as a fallback when OpenRouter is absent.
        (None, "oa-key", "oa-key", "https://api.openai.com/v1"),
    ],
)
def test_provider_config_prefers_openrouter_then_openai(
    monkeypatch, or_key, oa_key, expected_key, expected_url
):
    if or_key is None:
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    else:
        monkeypatch.setenv("OPENROUTER_API_KEY", or_key)
    if oa_key is None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    else:
        monkeypatch.setenv("OPENAI_API_KEY", oa_key)

    key, url = llm_client._provider_config()
    assert key == expected_key
    assert url == expected_url


def test_provider_config_requires_at_least_one_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY or OPENAI_API_KEY"):
        llm_client._provider_config()


def test_provider_config_respects_explicit_base_urls(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    monkeypatch.setenv("OPENAI_API_KEY", "oa-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://custom.example/v1")
    key, url = llm_client._provider_config()
    assert key == "or-key"
    assert url == "https://custom.example/v1"


@pytest.mark.asyncio
async def test_ask_returns_content_usage_and_cost(monkeypatch):
    async def fake_create(**_kwargs):
        return completion_response("hello", 100, 25)

    monkeypatch.setattr(llm_client.client.chat.completions, "create", fake_create)
    result = await llm_client.ask("say hello")
    assert result["response"] == "hello"
    assert result["prompt_tokens"] == 100
    assert result["completion_tokens"] == 25
    assert result["estimated_cost_usd"] == 0.0


@pytest.mark.asyncio
@pytest.mark.parametrize("transient_error", [APITimeoutError, RateLimitError, APIError])
async def test_ask_retries_transient_provider_errors(monkeypatch, transient_error):
    attempts = 0

    async def fake_create(**_kwargs):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise transient_error.__new__(transient_error)
        return completion_response("recovered")

    monkeypatch.setattr(llm_client.client.chat.completions, "create", fake_create)
    result = await llm_client.ask.retry_with(wait=wait_none())("retry me")
    assert result["response"] == "recovered"
    assert attempts == 3


@pytest.mark.asyncio
async def test_ask_does_not_retry_non_transient_errors(monkeypatch):
    attempts = 0

    async def fake_create(**_kwargs):
        nonlocal attempts
        attempts += 1
        raise ValueError("bad request")

    monkeypatch.setattr(llm_client.client.chat.completions, "create", fake_create)
    with pytest.raises(ValueError, match="bad request"):
        await llm_client.ask.retry_with(wait=wait_none())("do not retry")
    assert attempts == 1


@pytest.mark.asyncio
async def test_ask_stream_yields_only_non_empty_deltas(monkeypatch):
    chunks = [
        SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content="Hel"))]
        ),
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=None))]),
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="lo"))]),
    ]

    class FakeStream:
        def __aiter__(self):
            return self._iterator()

        async def _iterator(self):
            for chunk in chunks:
                yield chunk

    async def fake_create(**kwargs):
        assert kwargs["stream"] is True
        return FakeStream()

    monkeypatch.setattr(llm_client.client.chat.completions, "create", fake_create)
    result = [chunk async for chunk in llm_client.ask_stream("hello")]
    assert result == ["Hel", "lo"]


@pytest.mark.asyncio
async def test_ask_stream_honors_pinned_tier(monkeypatch):
    """The streaming path must use the requested tier, not the router default."""
    monkeypatch.setenv("MODEL_NAME", "main/model")
    monkeypatch.setenv("MODEL_CHEAP", "cheap/model")
    seen = {}

    class FakeStream:
        def __aiter__(self):
            return self._iterator()

        async def _iterator(self):
            yield SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="ok"))]
            )

    async def fake_create(**kwargs):
        seen["model"] = kwargs["model"]
        return FakeStream()

    monkeypatch.setattr(llm_client.client.chat.completions, "create", fake_create)
    # A complexity-marked prompt would normally route to "powerful"; pinning
    # "cheap" must win.
    result = [
        chunk
        async for chunk in llm_client.ask_stream(
            "debug this architecture tradeoff", tier="cheap"
        )
    ]
    assert result == ["ok"]
    assert seen["model"] == "cheap/model"


@pytest.mark.asyncio
async def test_extract_ticket_accepts_plain_json(monkeypatch):
    payload = {
        "summary": "Customer cannot log in.",
        "category": "account",
        "urgency": "high",
        "customer_sentiment": "negative",
    }

    async def fake_create(**_kwargs):
        return completion_response(json.dumps(payload))

    monkeypatch.setattr(llm_client.client.chat.completions, "create", fake_create)
    result = await llm_client.extract_ticket_info("I cannot log in")
    assert result.model_dump() == payload


@pytest.mark.asyncio
async def test_extract_ticket_strips_json_code_fences(monkeypatch):
    fence = chr(96) * 3
    raw = (
        fence
        + 'json\n{"summary":"Double charge","category":"billing","urgency":"medium","customer_sentiment":"negative"}\n'
        + fence
    )

    async def fake_create(**_kwargs):
        return completion_response(raw)

    monkeypatch.setattr(llm_client.client.chat.completions, "create", fake_create)
    result = await llm_client.extract_ticket_info("I was charged twice")
    assert result.category == "billing"


@pytest.mark.asyncio
async def test_extract_ticket_rejects_malformed_json(monkeypatch):
    async def fake_create(**_kwargs):
        return completion_response("not json")

    monkeypatch.setattr(llm_client.client.chat.completions, "create", fake_create)
    with pytest.raises(ValueError, match="invalid structured output"):
        await llm_client.extract_ticket_info("broken")


@pytest.mark.asyncio
async def test_extract_ticket_rejects_schema_violation(monkeypatch):
    payload = {
        "summary": "bad",
        "category": "refund",
        "urgency": "high",
        "customer_sentiment": "negative",
    }

    async def fake_create(**_kwargs):
        return completion_response(json.dumps(payload))

    monkeypatch.setattr(llm_client.client.chat.completions, "create", fake_create)
    with pytest.raises(ValueError, match="invalid structured output"):
        await llm_client.extract_ticket_info("invalid category")


@pytest.mark.asyncio
async def test_ask_stops_after_three_transient_failures(monkeypatch):
    attempts = 0

    async def fake_create(**_kwargs):
        nonlocal attempts
        attempts += 1
        raise RateLimitError.__new__(RateLimitError)

    monkeypatch.setattr(llm_client.client.chat.completions, "create", fake_create)

    with pytest.raises(RateLimitError):
        await llm_client.ask.retry_with(wait=wait_none())("always fails")

    assert attempts == 3


@pytest.mark.asyncio
async def test_extract_ticket_retries_transient_provider_error(monkeypatch):
    attempts = 0

    async def fake_create(**_kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RateLimitError.__new__(RateLimitError)
        return completion_response(
            '{"summary":"Resolved","category":"technical",'
            '"urgency":"low","customer_sentiment":"neutral"}'
        )

    monkeypatch.setattr(llm_client.client.chat.completions, "create", fake_create)
    result = await llm_client.extract_ticket_info.retry_with(wait=wait_none())("retry")

    assert result.category == "technical"
    assert attempts == 2
