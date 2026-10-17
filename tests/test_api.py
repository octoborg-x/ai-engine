import os

os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("MODEL_NAME", "cohere/north-mini-code:free")

import pytest
from starlette.requests import Request
from starlette.responses import Response

import app.main as api
from app.llm.schemas import TicketExtraction
from app.security.rate_limit import InMemoryRateLimiter


class FakeRateLimitError(Exception):
    pass


class FakeTimeoutError(Exception):
    pass


class FakeAPIError(Exception):
    pass


@pytest.mark.asyncio
async def test_health_returns_ok():
    assert api.health() == {"status": "ok"}


@pytest.mark.asyncio
async def test_chat_returns_validated_response(monkeypatch):
    async def fake_ask(prompt, tier=None):
        assert prompt == "hello"
        return {
            "response": "Hi!",
            "model": "test/model",
            "route": "balanced",
            "prompt_tokens": 3,
            "completion_tokens": 2,
            "estimated_cost_usd": 0.001,
            "latency_ms": 10.0,
            "success": True,
        }

    monkeypatch.setattr(api, "ask", fake_ask)
    result = await api.chat(api.ChatRequest(prompt="hello"))
    assert result.response == "Hi!"
    assert result.prompt_tokens == 3
    assert result.completion_tokens == 2
    assert result.estimated_cost_usd == 0.001


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exception_type", "expected_status", "expected_detail"),
    [
        (FakeRateLimitError, 429, "Rate limited by provider, try again shortly"),
        (FakeTimeoutError, 504, "LLM provider timed out"),
        (FakeAPIError, 502, "LLM provider error: upstream failure"),
        (RuntimeError, 500, "Unexpected error: unexpected failure"),
    ],
)
async def test_chat_maps_provider_failures_to_http_errors(
    monkeypatch, exception_type, expected_status, expected_detail
):
    async def failing_ask(_prompt, tier=None):
        message = (
            "upstream failure"
            if exception_type is FakeAPIError
            else "unexpected failure"
        )
        raise exception_type(message)

    monkeypatch.setattr(api, "RateLimitError", FakeRateLimitError)
    monkeypatch.setattr(api, "APITimeoutError", FakeTimeoutError)
    monkeypatch.setattr(api, "APIError", FakeAPIError)
    monkeypatch.setattr(api, "ask", failing_ask)

    with pytest.raises(api.HTTPException) as exc_info:
        await api.chat(api.ChatRequest(prompt="hello"))

    assert exc_info.value.status_code == expected_status
    assert exc_info.value.detail == expected_detail


@pytest.mark.asyncio
async def test_stream_endpoint_returns_streaming_response(monkeypatch):
    async def fake_stream(prompt, tier=None):
        assert prompt == "hello"
        yield "Hel"
        yield "lo"

    monkeypatch.setattr(api, "ask_stream", fake_stream)
    response = await api.chat_stream(api.ChatRequest(prompt="hello"))
    assert isinstance(response, api.StreamingResponse)
    assert response.media_type == "text/event-stream"
    assert response.body_iterator is not None


@pytest.mark.asyncio
async def test_stream_endpoint_forwards_selected_tier(monkeypatch):
    seen = {}

    async def fake_stream(prompt, tier=None):
        seen["tier"] = tier
        yield "ok"

    monkeypatch.setattr(api, "ask_stream", fake_stream)
    response = await api.chat_stream(api.ChatRequest(prompt="hello", tier="main"))
    async for _ in response.body_iterator:
        pass
    assert seen["tier"] == "main"


@pytest.mark.asyncio
async def test_stream_endpoint_surfaces_provider_error_before_200(monkeypatch):
    """A provider failing before the first chunk must raise, not stream a 200."""
    from openai import RateLimitError

    async def failing_stream(prompt, tier=None):
        raise RateLimitError.__new__(RateLimitError)
        yield  # pragma: no cover — never reached

    monkeypatch.setattr(api, "ask_stream", failing_stream)
    with pytest.raises(api.HTTPException) as exc_info:
        await api.chat_stream(api.ChatRequest(prompt="hello"))
    assert exc_info.value.status_code == 429
    assert "try again shortly" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_stream_endpoint_empty_provider_stream(monkeypatch):
    """A provider that ends without any chunk is an empty successful stream."""

    async def empty_stream(prompt, tier=None):
        if False:
            yield "never"

    monkeypatch.setattr(api, "ask_stream", empty_stream)
    response = await api.chat_stream(api.ChatRequest(prompt="hello"))
    collected = [chunk async for chunk in response.body_iterator]
    assert collected == []


@pytest.mark.asyncio
async def test_extract_ticket_returns_validated_model(monkeypatch):
    async def fake_extract(message):
        assert message == "My card was charged twice"
        return TicketExtraction(
            summary="Customer was charged twice.",
            category="billing",
            urgency="high",
            customer_sentiment="negative",
        )

    monkeypatch.setattr(api, "extract_ticket_info", fake_extract)
    result = await api.extract_ticket(
        api.TicketRequest(message="My card was charged twice")
    )
    assert result.category == "billing"
    assert result.urgency == "high"
    assert result.customer_sentiment == "negative"


@pytest.mark.asyncio
async def test_extract_ticket_maps_invalid_output_to_422(monkeypatch):
    async def fake_extract(_message):
        raise ValueError("Model returned invalid structured output")

    monkeypatch.setattr(api, "extract_ticket_info", fake_extract)
    with pytest.raises(api.HTTPException) as exc_info:
        await api.extract_ticket(api.TicketRequest(message="broken output"))

    assert exc_info.value.status_code == 422
    assert "invalid structured output" in exc_info.value.detail


@pytest.mark.asyncio
async def test_chat_security_middleware_rate_limits_before_auth(monkeypatch):
    limiter = InMemoryRateLimiter(limit=1, window_seconds=60)
    monkeypatch.setattr(api, "rate_limiter", limiter)
    monkeypatch.setenv("API_AUTH_TOKEN", "secret-token")

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/chat",
        "headers": [(b"authorization", b"Bearer secret-token")],
        "client": ("test-client", 1234),
        "query_string": b"",
        "scheme": "http",
        "server": ("test", 80),
        "root_path": "",
        "http_version": "1.1",
    }
    request = Request(scope)
    called = False

    async def call_next(_request):
        nonlocal called
        called = True
        return Response("ok")

    await api.api_security_middleware(request, call_next)
    assert called is True

    limited = await api.api_security_middleware(request, call_next)
    assert limited.status_code == 429


@pytest.mark.asyncio
async def test_chat_security_middleware_returns_401_not_500(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "secret-token")
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/ask",
        "headers": [],
        "client": ("test-client", 1234),
        "query_string": b"",
        "scheme": "http",
        "server": ("test", 80),
        "root_path": "",
        "http_version": "1.1",
    }

    async def call_next(_request):
        raise AssertionError("call_next must not run without a valid token")

    response = await api.api_security_middleware(Request(scope), call_next)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_ask_returns_grounded_answer_with_sources(monkeypatch):
    seen_prompt = {}

    async def fake_ask(prompt, tier=None):
        seen_prompt["value"] = prompt
        return {
            "response": "Refunds are allowed within 30 days [S1].",
            "model": "test/model",
            "route": "balanced",
            "prompt_tokens": 10,
            "completion_tokens": 8,
            "estimated_cost_usd": 0.002,
            "latency_ms": 12.0,
            "success": True,
        }

    monkeypatch.setattr(api, "ask", fake_ask)

    result = await api.ask_endpoint(api.AskRequest(query="what is the refund policy?"))

    assert result.query == "what is the refund policy?"
    assert "[S1]" in result.context
    assert result.sources
    assert result.retrieved_ids == [s.chunk_id for s in result.sources]
    assert result.answer == "Refunds are allowed within 30 days [S1]."
    assert "what is the refund policy?" in seen_prompt["value"]
    assert result.citations["valid_citations"] == ["S1"]


@pytest.mark.asyncio
async def test_ask_maps_provider_failures_to_http_errors(monkeypatch):
    async def failing_ask(_prompt, tier=None):
        raise FakeAPIError("upstream failure")

    monkeypatch.setattr(api, "APIError", FakeAPIError)
    monkeypatch.setattr(api, "ask", failing_ask)

    with pytest.raises(api.HTTPException) as exc_info:
        await api.ask_endpoint(api.AskRequest(query="what is the refund policy?"))

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "LLM provider error: upstream failure"


def test_ask_is_distinct_from_chat_in_openapi():
    """`/ask` takes a `query`; `/chat` takes a `prompt`."""
    schema = api.app.openapi()
    ask_body = schema["paths"]["/ask"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    chat_body = schema["paths"]["/chat"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert "AskRequest" in ask_body["$ref"]
    assert "ChatRequest" in chat_body["$ref"]


async def _sse_events(response) -> list[dict]:
    """Decode the raw SSE body into event payloads."""
    import json

    body = "".join([chunk async for chunk in response.body_iterator])
    return [
        json.loads(line[len("data: ") :])
        for line in body.splitlines()
        if line.startswith("data: ")
    ]


@pytest.mark.asyncio
async def test_ask_stream_endpoint_emits_deltas_then_done(monkeypatch):
    """The streaming endpoint returns SSE delta events and a done event."""
    seen_messages = {}

    def fake_stream_meta(messages, tier=None, route_text=None):
        async def gen():
            seen_messages["system"] = messages[0]["role"]
            seen_messages["route_text"] = route_text
            yield "Ref", None
            yield "unds", None
            yield (
                "",
                {
                    "model": "test/model",
                    "route": "balanced",
                    "route_reason": "test",
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "estimated_cost_usd": 0.002,
                    "latency_ms": 1500.0,
                    "ttft_ms": 800.0,
                    "success": True,
                },
            )

        return gen()

    monkeypatch.setattr(api, "stream_chat_meta", fake_stream_meta)
    response = await api.ask_stream_endpoint(
        api.AskRequest(query="what is the refund policy?")
    )
    assert isinstance(response, api.StreamingResponse)
    assert response.media_type == "text/event-stream"

    events = await _sse_events(response)
    assert [e["type"] for e in events] == ["delta", "delta", "done"]
    assert events[0]["text"] == "Ref"
    assert events[1]["text"] == "unds"

    answer = events[-1]["answer"]
    assert answer["answer"] == "Refunds"
    assert answer["ttft_ms"] == 800.0
    assert answer["latency_ms"] == 1500.0
    assert answer["prompt_tokens"] == 10
    assert answer["completion_tokens"] == 5
    assert answer["model"] == "test/model"
    assert answer["candidates"]
    assert seen_messages["system"] == "system"
    assert seen_messages["route_text"] == "what is the refund policy?"


@pytest.mark.asyncio
async def test_ask_stream_endpoint_rejects_empty_query():
    with pytest.raises(api.HTTPException) as exc_info:
        await api.ask_stream_endpoint(api.AskRequest(query="   "))
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_ask_stream_endpoint_surfaces_provider_error_before_200(monkeypatch):
    from openai import RateLimitError

    def failing_stream_meta(messages, tier=None, route_text=None):
        async def gen():
            raise RateLimitError.__new__(RateLimitError)
            yield  # pragma: no cover — never reached

        return gen()

    monkeypatch.setattr(api, "stream_chat_meta", failing_stream_meta)
    with pytest.raises(api.HTTPException) as exc_info:
        await api.ask_stream_endpoint(
            api.AskRequest(query="what is the refund policy?")
        )
    assert exc_info.value.status_code == 429
    assert "try again shortly" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_authenticate_accepts_bearer_token(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "secret-token")
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/chat",
        "headers": [(b"authorization", b"Bearer secret-token")],
        "client": ("test-client", 1234),
        "query_string": b"",
        "scheme": "http",
        "server": ("test", 80),
        "root_path": "",
        "http_version": "1.1",
    }
    assert api.authenticate(Request(scope)) == "api-token"


@pytest.mark.asyncio
async def test_authenticate_rejects_invalid_token(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "secret-token")
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/chat",
        "headers": [(b"authorization", b"Bearer wrong")],
        "client": ("test-client", 1234),
        "query_string": b"",
        "scheme": "http",
        "server": ("test", 80),
        "root_path": "",
        "http_version": "1.1",
    }
    with pytest.raises(api.HTTPException) as exc_info:
        api.authenticate(Request(scope))
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_health_no_llm_secret(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert api.health() == {"status": "ok"}


@pytest.mark.asyncio
async def test_ready_with_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    result = api.ready()
    assert result == {"status": "ready"}


@pytest.mark.asyncio
async def test_ready_without_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = api.ready()
    assert result.status_code == 503


@pytest.mark.asyncio
async def test_ready_with_openai_fallback_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    result = api.ready()
    assert result == {"status": "ready"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/chat"),
        ("POST", "/ask"),
        ("POST", "/ask/stream"),
        ("POST", "/chat/stream"),
        ("POST", "/extract-ticket"),
        ("POST", "/jobs"),
        ("GET", "/jobs/job-123"),
        ("GET", "/metrics"),
    ],
)
async def test_protected_endpoints_reject_missing_token(monkeypatch, method, path):
    monkeypatch.setenv("API_AUTH_TOKEN", "secret-token")
    monkeypatch.setattr(api, "rate_limiter", InMemoryRateLimiter(100, 60))
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [],
        "client": ("test-client", 1234),
        "query_string": b"",
        "scheme": "http",
        "server": ("test", 80),
        "root_path": "",
        "http_version": "1.1",
    }
    called = False

    async def call_next(_request):
        nonlocal called
        called = True
        return Response("ok")

    response = await api.api_security_middleware(Request(scope), call_next)
    assert response.status_code == 401
    assert called is False


def test_health_and_readiness_probes_remain_public():
    health_scope = {
        "type": "http",
        "method": "GET",
        "path": "/health",
        "headers": [],
        "client": ("test-client", 1234),
        "query_string": b"",
        "scheme": "http",
        "server": ("test", 80),
        "root_path": "",
        "http_version": "1.1",
    }
    ready_scope = {**health_scope, "path": "/ready"}
    assert api._requires_authentication(Request(health_scope)) is False
    assert api._requires_authentication(Request(ready_scope)) is False
