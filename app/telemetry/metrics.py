# Prices per 1M tokens, in USD. Update if you switch models.
import logging

# Free models are $0 — but structure this to work for paid models too.
MODEL_PRICING = {
    "cohere/north-mini-code:free": {"input": 0.0, "output": 0.0},
}

logger = logging.getLogger(__name__)

# Aggregated production metrics — no prompt/user content stored.
_METRICS = {
    "http_requests_total": {},
    "http_latency_ms_sum": {},
    "http_latency_ms_count": {},
    "llm_calls_total": {},
    "llm_latency_ms_sum": {},
    "llm_latency_ms_count": {},
    "llm_input_tokens_total": 0,
    "llm_output_tokens_total": 0,
    "llm_total_tokens_total": 0,
    "llm_estimated_cost_usd_total": 0.0,
}


class MetricsCollector:
    @staticmethod
    def reset() -> None:
        _METRICS["http_requests_total"].clear()
        _METRICS["http_latency_ms_sum"].clear()
        _METRICS["http_latency_ms_count"].clear()
        _METRICS["llm_calls_total"].clear()
        _METRICS["llm_latency_ms_sum"].clear()
        _METRICS["llm_latency_ms_count"].clear()
        _METRICS["llm_input_tokens_total"] = 0
        _METRICS["llm_output_tokens_total"] = 0
        _METRICS["llm_total_tokens_total"] = 0
        _METRICS["llm_estimated_cost_usd_total"] = 0.0

    @staticmethod
    def record_http(method: str, path: str, status: int, latency_ms: float) -> None:
        key = (method, path, str(status))
        _METRICS["http_requests_total"][key] = (
            _METRICS["http_requests_total"].get(key, 0) + 1
        )
        lat_key = (method, path)
        _METRICS["http_latency_ms_sum"][lat_key] = (
            _METRICS["http_latency_ms_sum"].get(lat_key, 0.0) + latency_ms
        )
        _METRICS["http_latency_ms_count"][lat_key] = (
            _METRICS["http_latency_ms_count"].get(lat_key, 0) + 1
        )

    # pylint: disable=too-many-arguments
    @staticmethod
    def record_llm(
        model: str,
        status: str,
        latency_ms: float,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        cost_usd: float | None = None,
    ) -> None:
        key = (model, status)
        _METRICS["llm_calls_total"][key] = _METRICS["llm_calls_total"].get(key, 0) + 1
        lat_key = model
        _METRICS["llm_latency_ms_sum"][lat_key] = (
            _METRICS["llm_latency_ms_sum"].get(lat_key, 0.0) + latency_ms
        )
        _METRICS["llm_latency_ms_count"][lat_key] = (
            _METRICS["llm_latency_ms_count"].get(lat_key, 0) + 1
        )
        if input_tokens is not None:
            _METRICS["llm_input_tokens_total"] += input_tokens
        if output_tokens is not None:
            _METRICS["llm_output_tokens_total"] += output_tokens
        if input_tokens is not None and output_tokens is not None:
            _METRICS["llm_total_tokens_total"] += input_tokens + output_tokens
        if cost_usd is not None:
            _METRICS["llm_estimated_cost_usd_total"] += cost_usd

    @staticmethod
    def snapshot() -> dict:
        result = {
            "http_requests_total": {
                str(k): v for k, v in _METRICS["http_requests_total"].items()
            },
            "http_latency_ms_avg": {},
            "llm_calls_total": {
                str(k): v for k, v in _METRICS["llm_calls_total"].items()
            },
            "llm_latency_ms_avg": {},
            "llm_input_tokens_total": _METRICS["llm_input_tokens_total"],
            "llm_output_tokens_total": _METRICS["llm_output_tokens_total"],
            "llm_total_tokens_total": _METRICS["llm_total_tokens_total"],
            "llm_estimated_cost_usd_total": round(
                _METRICS["llm_estimated_cost_usd_total"], 6
            ),
        }
        for lat_key in _METRICS["http_latency_ms_sum"]:
            s = _METRICS["http_latency_ms_sum"][lat_key]
            c = _METRICS["http_latency_ms_count"][lat_key]
            result["http_latency_ms_avg"][str(lat_key)] = round(s / c, 2) if c else 0.0
        for lat_key in _METRICS["llm_latency_ms_sum"]:
            s = _METRICS["llm_latency_ms_sum"][lat_key]
            c = _METRICS["llm_latency_ms_count"][lat_key]
            result["llm_latency_ms_avg"][lat_key] = round(s / c, 2) if c else 0.0
        return result


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


def record_call(
    *,
    model: str,
    tier: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    latency_ms: float,
    status: str,
    attempt: int,
) -> None:
    """Emit one structured LLM telemetry event without storing prompt contents."""
    input_tokens = prompt_tokens if prompt_tokens is not None else None
    output_tokens = completion_tokens if completion_tokens is not None else None
    total_tokens = (
        input_tokens + output_tokens
        if input_tokens is not None and output_tokens is not None
        else None
    )
    cost = (
        calculate_cost(model, input_tokens, output_tokens)
        if input_tokens is not None and output_tokens is not None
        else None
    )
    extra = {
        "event": "llm.call",
        "model": model,
        "tier": tier,
        "latency_ms": latency_ms,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost_usd": cost,
        "status": status,
        "attempt": attempt,
    }
    logger.info("llm call", extra=extra)
    MetricsCollector.record_llm(
        model=model,
        status=status,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost,
    )
