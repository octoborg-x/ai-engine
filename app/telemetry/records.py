"""Bounded in-memory request and LLM-call records for the observability view.

These records back the console's "recent requests" table: each HTTP request and
each LLM call is captured with its correlation IDs, latency, and usage. Only
metadata is stored — never prompt or completion content. The buffers are
process-local and intentionally small; a production deployment would forward the
same structured events to a log/metrics store instead.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import asdict, dataclass, field

from app.telemetry.logging import get_request_id, get_trace_id

_MAX_RECORDS = 200


@dataclass
class RequestRecord:
    """One completed HTTP request."""

    request_id: str
    trace_id: str
    method: str
    path: str
    status: int
    latency_ms: float
    timestamp: float = field(default_factory=time.time)

    @property
    def success(self) -> bool:
        return self.status < 400


@dataclass
class LlmCallRecord:
    """One LLM provider call (including retries as separate records)."""

    request_id: str
    trace_id: str
    model: str
    tier: str
    status: str
    latency_ms: float
    attempt: int
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    cost_usd: float | None
    timestamp: float = field(default_factory=time.time)


_requests: deque[RequestRecord] = deque(maxlen=_MAX_RECORDS)
_llm_calls: deque[LlmCallRecord] = deque(maxlen=_MAX_RECORDS)


def record_request(method: str, path: str, status: int, latency_ms: float) -> None:
    """Append one HTTP request record with the active correlation IDs."""
    _requests.append(
        RequestRecord(
            request_id=get_request_id(),
            trace_id=get_trace_id(),
            method=method,
            path=path,
            status=status,
            latency_ms=round(latency_ms, 2),
        )
    )


def record_llm_call(
    *,
    model: str,
    tier: str,
    status: str,
    latency_ms: float,
    attempt: int,
    input_tokens: int | None,
    output_tokens: int | None,
    cost_usd: float | None,
) -> None:
    """Append one LLM call record, linked to the request that triggered it."""
    total = (
        input_tokens + output_tokens
        if input_tokens is not None and output_tokens is not None
        else None
    )
    _llm_calls.append(
        LlmCallRecord(
            request_id=get_request_id(),
            trace_id=get_trace_id(),
            model=model,
            tier=tier,
            status=status,
            latency_ms=round(latency_ms, 2),
            attempt=attempt,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total,
            cost_usd=cost_usd,
        )
    )


def recent_requests(limit: int = 50) -> list[dict]:
    """Return the most recent request records, newest first."""
    items = list(_requests)[-limit:]
    return [asdict(r) | {"success": r.success} for r in reversed(items)]


def recent_llm_calls(limit: int = 50) -> list[dict]:
    """Return the most recent LLM call records, newest first."""
    items = list(_llm_calls)[-limit:]
    return [asdict(c) for c in reversed(items)]


def reset() -> None:
    """Clear all records (used by tests)."""
    _requests.clear()
    _llm_calls.clear()
