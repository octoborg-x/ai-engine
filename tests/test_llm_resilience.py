import asyncio

import pytest

from app.llm.resilience import (
    CircuitBreaker,
    CircuitOpenError,
    _llm_circuit_breakers,
    breaker_for_tier,
)


@pytest.mark.asyncio
async def test_successful_call_returns_result_and_keeps_circuit_closed():
    breaker = CircuitBreaker(failure_threshold=2, reset_timeout_seconds=0.01)

    result = await breaker.call(lambda: _value("ok"), timeout_seconds=0.1)

    assert result == "ok"
    assert breaker.state == "CLOSED"
    assert breaker.failure_count == 0


@pytest.mark.asyncio
async def test_timeout_is_enforced_and_counts_as_failure():
    breaker = CircuitBreaker(failure_threshold=1, reset_timeout_seconds=0.01)

    with pytest.raises(TimeoutError):
        await breaker.call(lambda: _sleep(0.1), timeout_seconds=0.001)

    assert breaker.state == "OPEN"


@pytest.mark.asyncio
async def test_circuit_opens_after_threshold_and_fails_fast():
    breaker = CircuitBreaker(failure_threshold=2, reset_timeout_seconds=10)
    calls = 0

    async def fail():
        nonlocal calls
        calls += 1
        raise OSError("provider unavailable")

    for _ in range(2):
        with pytest.raises(OSError):
            await breaker.call(fail, timeout_seconds=0.1)

    with pytest.raises(CircuitOpenError):
        await breaker.call(fail, timeout_seconds=0.1)

    assert calls == 2
    assert breaker.state == "OPEN"


@pytest.mark.asyncio
async def test_successful_half_open_probe_closes_circuit():
    breaker = CircuitBreaker(failure_threshold=1, reset_timeout_seconds=0.001)

    with pytest.raises(OSError):
        await breaker.call(lambda: _fail(), timeout_seconds=0.1)

    await asyncio.sleep(0.005)
    assert (
        await breaker.call(lambda: _value("recovered"), timeout_seconds=0.1)
        == "recovered"
    )
    assert breaker.state == "CLOSED"
    assert breaker.failure_count == 0


@pytest.mark.asyncio
async def test_failed_half_open_probe_reopens_circuit():
    breaker = CircuitBreaker(failure_threshold=1, reset_timeout_seconds=0.001)

    with pytest.raises(OSError):
        await breaker.call(lambda: _fail(), timeout_seconds=0.1)

    await asyncio.sleep(0.005)
    with pytest.raises(OSError):
        await breaker.call(lambda: _fail(), timeout_seconds=0.1)

    assert breaker.state == "OPEN"


async def _value(value):
    return value


async def _sleep(seconds):
    await asyncio.sleep(seconds)


async def _fail():
    raise OSError("provider unavailable")


def _reset_breaker_registry():
    """Forget lazily created breakers so tests run in isolation."""
    _llm_circuit_breakers.clear()


@pytest.mark.asyncio
async def test_breaker_for_tier_isolates_openai_compatible_from_active():
    _reset_breaker_registry()
    active = breaker_for_tier("main")
    compat = breaker_for_tier("openai-compatible")
    assert active is not compat
    assert breaker_for_tier("balanced") is active
    assert breaker_for_tier("openai-compatible") is compat
    _reset_breaker_registry()


@pytest.mark.asyncio
async def test_openai_compatible_breaker_untouched_by_active_failures():
    """Failures on the active backend must not open the compat one."""
    _reset_breaker_registry()
    active = breaker_for_tier("main")
    active.failure_threshold = 1
    active.reset_timeout_seconds = 10

    with pytest.raises(OSError):
        await active.call(_fail, timeout_seconds=0.1)
    with pytest.raises(CircuitOpenError):
        await active.call(_fail, timeout_seconds=0.1)

    compat = breaker_for_tier("openai-compatible")
    assert compat.state == "CLOSED"
    assert await compat.call(lambda: _value("ok"), timeout_seconds=0.1) == "ok"
    assert compat.state == "CLOSED"
    _reset_breaker_registry()
