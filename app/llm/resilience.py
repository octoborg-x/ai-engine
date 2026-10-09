"""Small, dependency-free timeout and circuit-breaker primitives for provider calls."""
import asyncio
import logging
import os
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)


class CircuitOpenError(RuntimeError):
    """Raised when the provider circuit is open and calls are rejected."""


class CircuitBreaker:
    """Async circuit breaker with CLOSED, OPEN, and HALF_OPEN states."""

    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout_seconds: float = 30.0,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if reset_timeout_seconds <= 0:
            raise ValueError("reset_timeout_seconds must be > 0")
        self.failure_threshold = failure_threshold
        self.reset_timeout_seconds = reset_timeout_seconds
        self.state = "CLOSED"
        self.failure_count = 0
        self.opened_at: float | None = None
        self._half_open_probe_in_flight = False
        self._lock = asyncio.Lock()

    async def call(
        self, operation: Callable[[], Awaitable[T]], timeout_seconds: float
    ) -> T:
        await self._acquire_permission()
        try:
            result = await asyncio.wait_for(operation(), timeout=timeout_seconds)
        except Exception as exc:
            await self._record_failure(exc)
            raise
        await self._record_success()
        return result

    async def _acquire_permission(self) -> None:
        async with self._lock:
            if self.state == "OPEN":
                assert self.opened_at is not None
                if time.monotonic() - self.opened_at < self.reset_timeout_seconds:
                    logger.warning(
                        "LLM circuit rejected call",
                        extra={"event": "llm.circuit", "state": "OPEN"},
                    )
                    raise CircuitOpenError("LLM provider circuit is open")
                self.state = "HALF_OPEN"
                self._half_open_probe_in_flight = False
                logger.info(
                    "LLM circuit state changed",
                    extra={"event": "llm.circuit", "state": "HALF_OPEN"},
                )

            if self.state == "HALF_OPEN":
                if self._half_open_probe_in_flight:
                    raise CircuitOpenError("LLM provider half-open probe in progress")
                self._half_open_probe_in_flight = True

    async def _record_failure(self, exc: BaseException) -> None:
        async with self._lock:
            was_half_open = self.state == "HALF_OPEN"
            self.failure_count += 1
            if was_half_open or self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                self.opened_at = time.monotonic()
                self._half_open_probe_in_flight = False
                logger.error(
                    "LLM circuit opened",
                    extra={
                        "event": "llm.circuit",
                        "state": self.state,
                        "failure_count": self.failure_count,
                        "error_type": type(exc).__name__,
                    },
                )

    async def _record_success(self) -> None:
        async with self._lock:
            was_half_open = self.state == "HALF_OPEN"
            self.failure_count = 0
            self.state = "CLOSED"
            self.opened_at = None
            self._half_open_probe_in_flight = False
            if was_half_open:
                logger.info(
                    "LLM circuit closed after successful probe",
                    extra={"event": "llm.circuit", "state": self.state},
                )


llm_circuit_breaker = CircuitBreaker(
    failure_threshold=int(os.getenv("LLM_CIRCUIT_FAILURE_THRESHOLD", "5")),
    reset_timeout_seconds=float(os.getenv("LLM_CIRCUIT_RESET_SECONDS", "30")),
)
