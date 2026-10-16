import asyncio
import json
import logging
import os
import time
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from openai import APIError, APITimeoutError, AsyncOpenAI, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.llm.providers import resolve_provider
from app.llm.resilience import llm_circuit_breaker
from app.llm.router import route
from app.llm.schemas import TicketExtraction
from app.telemetry.metrics import calculate_cost, record_call

load_dotenv()

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


class _LazyCompletions:
    async def create(self, **kwargs):
        return await _get_client().chat.completions.create(**kwargs)


class _LazyChat:
    def __init__(self) -> None:
        self.completions = _LazyCompletions()


class _LazyClient:
    def __init__(self) -> None:
        self.chat = _LazyChat()


client = _LazyClient()


def _provider_config() -> tuple[str, str]:
    """Resolve (api_key, base_url): OpenRouter first, OpenAI next, generic last."""
    provider = resolve_provider()
    return provider.api_key, provider.base_url


def _get_client() -> AsyncOpenAI:
    """Build the provider client only when an LLM call is actually needed.

    This keeps non-LLM endpoints such as /health importable without secrets.
    Provider precedence is OpenRouter first, OpenAI (or any OpenAI-compatible
    endpoint such as Gemini) as a fallback.
    """
    global _client

    if _client is None:
        api_key, base_url = _provider_config()
        _client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
        )

    return _client


def _log_retry(retry_state) -> None:
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    logger.warning(
        "llm retry scheduled",
        extra={
            "event": "llm.retry",
            "attempt": retry_state.attempt_number,
            "status": "retrying",
            "error_type": type(exc).__name__ if exc else "unknown",
        },
    )


llm_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(
        (APITimeoutError, RateLimitError, APIError, asyncio.TimeoutError)
    ),
    before_sleep=_log_retry,
    reraise=True,
)


async def _completion(model: str, messages: list[dict[str, str]]):
    """Call the provider through the shared timeout and circuit-breaker layer."""
    timeout_seconds = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
    return await llm_circuit_breaker.call(
        lambda: client.chat.completions.create(model=model, messages=messages),
        timeout_seconds=timeout_seconds,
    )


@llm_retry
async def ask(prompt: str, tier: str | None = None) -> dict:
    decision = route("chat", prompt, force_tier=tier)
    started = time.perf_counter()
    usage = None
    status = "error"

    try:
        response = await _completion(
            decision.model,
            [{"role": "user", "content": prompt}],
        )
        usage = response.usage
        status = "success"
        return {
            "response": response.choices[0].message.content,
            "model": decision.model,
            "route": decision.tier,
            "route_reason": decision.reason,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "estimated_cost_usd": calculate_cost(
                decision.model, usage.prompt_tokens, usage.completion_tokens
            ),
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "success": True,
        }
    finally:
        record_call(
            model=decision.model,
            tier=decision.tier,
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            status=status,
            attempt=1,
        )


@llm_retry
async def complete_json(prompt: str, task: str = "extraction") -> tuple[dict, dict]:
    """Run a structured-output call and return (parsed_json, metadata).

    Shared by extraction-style features (ticket extraction, candidate
    screening). Uses the router's task mapping so structured work lands on the
    cheap tier, and records the same telemetry as the other LLM entry points.
    """
    decision = route(task, prompt)
    started = time.perf_counter()
    usage = None
    status = "error"
    raw = ""

    try:
        response = await _completion(
            decision.model,
            [{"role": "user", "content": prompt}],
        )
        usage = response.usage
        raw = response.choices[0].message.content.strip()
        if raw.startswith(chr(96) * 3):
            raw = raw.strip(chr(96)).removeprefix("json").strip()
        data = json.loads(raw)
        status = "success"
        meta = {
            "model": decision.model,
            "route": decision.tier,
            "route_reason": decision.reason,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "estimated_cost_usd": calculate_cost(
                decision.model, usage.prompt_tokens, usage.completion_tokens
            ),
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }
        return data, meta
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"Model returned invalid structured output: {raw}") from exc
    finally:
        record_call(
            model=decision.model,
            tier=decision.tier,
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            status=status,
            attempt=1,
        )


async def ask_stream(prompt: str, tier: str | None = None) -> AsyncGenerator[str, None]:
    decision = route("chat", prompt, force_tier=tier)
    started = time.perf_counter()
    status = "error"
    usage = None
    try:
        timeout_seconds = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
        stream = await llm_circuit_breaker.call(
            lambda: client.chat.completions.create(
                model=decision.model,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                stream_options={"include_usage": True},
            ),
            timeout_seconds=timeout_seconds,
        )
        async for chunk in stream:
            # With include_usage the final chunk carries usage; capture it so
            # token accounting works for streamed responses too. Providers vary
            # whether that chunk also has a (final, empty) choice.
            chunk_usage = getattr(chunk, "usage", None)
            if chunk_usage is not None:
                usage = chunk_usage
            choices = chunk.choices or []
            if choices and choices[0].delta.content:
                yield choices[0].delta.content
        status = "success"
    finally:
        record_call(
            model=decision.model,
            tier=decision.tier,
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            status=status,
            attempt=1,
        )


@llm_retry
async def extract_ticket_info(message: str) -> TicketExtraction:
    decision = route("extraction", message)
    started = time.perf_counter()
    usage = None
    status = "error"
    raw = ""

    prompt = f"""Extract structured information from this customer support message.

Respond with ONLY valid JSON, no other text, matching this exact structure:
{{
    "summary": "one sentence summary",
    "category": "billing" | "technical" | "account" | "other",
    "urgency": "low" | "medium" | "high",
    "customer_sentiment": "positive" | "neutral" | "negative"
}}

Customer message: {message}"""

    try:
        response = await _completion(
            decision.model,
            [{"role": "user", "content": prompt}],
        )
        usage = response.usage
        raw = response.choices[0].message.content.strip()

        if raw.startswith(chr(96) * 3):
            raw = raw.strip(chr(96)).removeprefix("json").strip()

        data = json.loads(raw)
        result = TicketExtraction(**data)
        status = "success"
        return result
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"Model returned invalid structured output: {raw}") from exc
    finally:
        record_call(
            model=decision.model,
            tier=decision.tier,
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            status=status,
            attempt=1,
        )
