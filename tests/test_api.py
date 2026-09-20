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
    async def fake_ask(prompt):
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
    async def failing_ask(_prompt):
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
    async def fake_stream(prompt):
        assert prompt == "hello"
        yield "Hel"
        yield "lo"

    monkeypatch.setattr(api, "ask_stream", fake_stream)
    response = await api.chat_stream(api.ChatRequest(prompt="hello"))
    assert isinstance(response, api.StreamingResponse)
    assert response.media_type == "text/event-stream"
    assert response.body_iterator is not None


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

    async def fake_ask(prompt):
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
    async def failing_ask(_prompt):
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
