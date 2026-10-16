"""Tier comparison benchmark.

Runs the same labeled prompt set through each routing tier (cheap, balanced,
powerful) and measures pass rate, latency percentiles, token usage, and cost.
This is the backend behind the console's Compare view — the numbers are
measured, not estimated.
"""

from __future__ import annotations

import time

from app.evals.engine import CHAT_PREFIX, _score_chat, load_cases, percentile
from app.llm.client import ask
from app.llm.router import _model_for

TIERS = ("cheap", "balanced", "powerful")


def _model_for_tier(tier: str) -> str:
    try:
        return _model_for(tier)
    except KeyError:
        return "unconfigured"


async def _run_tier(tier: str, cases: list[dict]) -> dict:
    rows = []
    for case in cases:
        started = time.perf_counter()
        passed = False
        tokens_in = tokens_out = 0
        cost = 0.0
        status = "ok"
        try:
            result = await ask(CHAT_PREFIX + case["input"], tier=tier)
            passed, _ = _score_chat(case, str(result["response"]))
            tokens_in = result["prompt_tokens"]
            tokens_out = result["completion_tokens"]
            cost = result["estimated_cost_usd"]
        except Exception as exc:  # noqa: BLE001 - provider failures are data
            status = f"error:{type(exc).__name__}"
        rows.append(
            {
                "id": case["id"],
                "passed": passed,
                "status": status,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "prompt_tokens": tokens_in,
                "completion_tokens": tokens_out,
                "estimated_cost_usd": cost,
            }
        )

    total = len(rows)
    passed = sum(1 for r in rows if r["passed"])
    latencies = [r["latency_ms"] for r in rows]
    errors = sum(1 for r in rows if r["status"] != "ok")
    return {
        "tier": tier,
        "model": _model_for_tier(tier),
        "cases": total,
        "passed": passed,
        "pass_rate": round(passed / total, 4) if total else None,
        "errors": errors,
        "latency_ms": {
            "average": round(sum(latencies) / total, 2) if total else None,
            "p50": percentile(latencies, 0.50),
            "p95": percentile(latencies, 0.95),
        },
        "tokens": {
            "average": (
                round(
                    sum(r["prompt_tokens"] + r["completion_tokens"] for r in rows)
                    / total,
                    1,
                )
                if total
                else None
            ),
            "input": sum(r["prompt_tokens"] for r in rows),
            "output": sum(r["completion_tokens"] for r in rows),
        },
        "cost": {
            "average_per_request_usd": (
                round(sum(r["estimated_cost_usd"] for r in rows) / total, 6)
                if total
                else None
            ),
            "total_usd": round(sum(r["estimated_cost_usd"] for r in rows), 6),
        },
    }


async def compare_tiers(limit: int) -> dict:
    """Benchmark every tier over the first ``limit`` labeled chat cases."""
    cases = list(load_cases("chat"))[:limit]
    results = [await _run_tier(tier, cases) for tier in TIERS]
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "cases_per_tier": len(cases),
        "results": results,
    }
