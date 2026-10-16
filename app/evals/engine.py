"""Evaluation engine: run labeled suites against the live model and score them.

This mirrors ``evals/run_eval.py`` but lives inside the application package so
the API can expose a bounded evaluation run. Scoring is deterministic and
keyword/field based — no LLM-as-judge — so results are reproducible.
"""

from __future__ import annotations

import json
import math
import time
from functools import cache
from pathlib import Path
from typing import Any

from app.llm.client import ask, complete_json

CHAT_PREFIX = (
    "Answer directly and accurately. Do not invent facts. "
    "If ambiguous, state what is missing or ask a focused clarification. "
    "For multilingual input, answer in the input language.\n\n"
)

# Suite name -> case-file stem. Kept small enough to run inside one request.
SUITE_FILES = {
    "chat": "chat_cases",
    "extraction": "extraction_cases",
    "classification": "classification_cases",
    "adversarial": "adversarial_cases",
    "retrieval": "retrieval_cases",
}

_CATEGORY_ENUM = {"billing", "technical", "account", "other"}
_URGENCY_ENUM = {"low", "medium", "high"}
_SENTIMENT_ENUM = {"positive", "neutral", "negative"}


def _cases_dir() -> Path:
    return Path(__file__).resolve().parent / "cases"


@cache
def load_cases(suite: str) -> tuple[dict, ...]:
    """Load one suite's cases from the packaged JSON file."""
    path = _cases_dir() / f"{SUITE_FILES[suite]}.json"
    with path.open(encoding="utf-8") as handle:
        return tuple(json.load(handle))


def suite_sizes() -> dict[str, int]:
    """Case count per suite, for the UI index."""
    return {suite: len(load_cases(suite)) for suite in SUITE_FILES}


def percentile(values: list[float], p: float) -> float | None:
    """Linear-interpolated percentile, matching the standalone runner."""
    if not values:
        return None
    ordered = sorted(values)
    rank = (len(ordered) - 1) * p
    low, high = math.floor(rank), math.ceil(rank)
    if low == high:
        return round(ordered[low], 2)
    return round(ordered[low] + (ordered[high] - ordered[low]) * (rank - low), 2)


def _contains_all(text: str, items: list[str]) -> bool:
    lowered = text.lower()
    return all(item.lower() in lowered for item in items)


def _contains_none(text: str, items: list[str]) -> bool:
    lowered = text.lower()
    return not any(item.lower() in lowered for item in items)


def _score_chat(case: dict, answer: str) -> tuple[bool, dict]:
    expected = case["expected"]
    concepts_ok = _contains_all(answer, expected.get("must_contain_concepts", []))
    forbidden_ok = _contains_none(answer, expected.get("must_not_contain", []))
    passed = concepts_ok and forbidden_ok
    return passed, {"concepts_ok": concepts_ok, "forbidden_ok": forbidden_ok}


def _score_extraction(case: dict, data: dict) -> tuple[bool, dict]:
    required = {"summary", "category", "urgency", "customer_sentiment"}
    schema_valid = required.issubset(data) and all(
        isinstance(data.get(field), str) for field in required
    )
    enums_valid = (
        data.get("category") in _CATEGORY_ENUM
        and data.get("urgency") in _URGENCY_ENUM
        and data.get("customer_sentiment") in _SENTIMENT_ENUM
    )
    expected = case["expected"]
    summary_ok = _contains_all(
        str(data.get("summary", "")), expected["summary_keywords"]
    )
    exact_ok = all(
        data.get(field) == expected[field]
        for field in ("category", "urgency", "customer_sentiment")
    )
    passed = schema_valid and enums_valid and summary_ok and exact_ok
    return passed, {
        "schema_valid": schema_valid,
        "enum_valid": enums_valid,
        "summary_ok": summary_ok,
        "exact_fields_ok": exact_ok,
    }


def _score_classification(case: dict, data: dict) -> tuple[bool, dict]:
    predicted = data.get("category")
    passed = predicted == case["expected"]["category"]
    return passed, {"predicted_category": predicted}


def _extraction_prompt(message: str) -> str:
    return (
        "Extract structured information from this customer support message.\n\n"
        "Respond with ONLY valid JSON matching this structure:\n"
        '{"summary": "one sentence", "category": "billing"|"technical"|'
        '"account"|"other", "urgency": "low"|"medium"|"high", '
        '"customer_sentiment": "positive"|"neutral"|"negative"}\n\n'
        f"Customer message: {message}"
    )


async def _run_case(suite: str, case: dict) -> dict:
    started = time.perf_counter()
    status = 200
    details: dict[str, Any]
    passed = False
    tokens_in = tokens_out = 0
    cost = 0.0
    try:
        if suite in {"extraction", "classification"}:
            data, meta = await complete_json(_extraction_prompt(case["input"]))
            if suite == "extraction":
                passed, details = _score_extraction(case, data)
            else:
                passed, details = _score_classification(case, data)
            tokens_in = meta["prompt_tokens"]
            tokens_out = meta["completion_tokens"]
            cost = meta["estimated_cost_usd"]
        else:
            result = await ask(CHAT_PREFIX + case["input"])
            passed, details = _score_chat(case, str(result["response"]))
            tokens_in = result["prompt_tokens"]
            tokens_out = result["completion_tokens"]
            cost = result["estimated_cost_usd"]
        details["outcome"] = "pass" if passed else "model_failure"
    except Exception as exc:  # noqa: BLE001 - provider/parse failures are data
        status = 0
        passed = False
        details = {"outcome": "api_error", "error_type": type(exc).__name__}
    return {
        "id": case["id"],
        "passed": passed,
        "status": status,
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "details": details,
        "prompt_tokens": tokens_in,
        "completion_tokens": tokens_out,
        "estimated_cost_usd": cost,
    }


def _summarize(suite: str, rows: list[dict]) -> dict:
    total = len(rows)
    api_errors = sum(r["details"].get("outcome") == "api_error" for r in rows)
    evaluated = [
        r for r in rows if r["details"].get("outcome") in {"pass", "model_failure"}
    ]
    passed = sum(r["details"].get("outcome") == "pass" for r in evaluated)
    schema_checks = [
        r["details"]["schema_valid"]
        for r in evaluated
        if "schema_valid" in r["details"]
    ]
    latencies = [r["latency_ms"] for r in rows]
    tokens_in = sum(r["prompt_tokens"] for r in rows)
    tokens_out = sum(r["completion_tokens"] for r in rows)
    cost = sum(r["estimated_cost_usd"] for r in rows)
    return {
        "suite": suite,
        "total_cases": total,
        "evaluated_cases": len(evaluated),
        "passed": passed,
        "model_failures": len(evaluated) - passed,
        "api_errors": api_errors,
        "accuracy": round(passed / len(evaluated), 4) if evaluated else None,
        "api_error_rate": round(api_errors / total, 4) if total else 0.0,
        "structured_output_validity": (
            round(sum(schema_checks) / len(schema_checks), 4) if schema_checks else None
        ),
        "latency_ms": {
            "average": round(sum(latencies) / len(latencies), 2) if latencies else None,
            "p50": percentile(latencies, 0.50),
            "p95": percentile(latencies, 0.95),
            "p99": percentile(latencies, 0.99),
        },
        "tokens": {
            "input": tokens_in,
            "output": tokens_out,
            "total": tokens_in + tokens_out,
        },
        "cost": {
            "total_usd": round(cost, 6),
            "average_per_request_usd": round(cost / total, 6) if total else 0.0,
        },
    }


async def run_suite(suite: str, limit: int) -> dict:
    """Run up to ``limit`` cases of one suite and return the summary."""
    cases = load_cases(suite)[:limit]
    rows = [await _run_case(suite, case) for case in cases]
    return _summarize(suite, rows)


def run_retrieval_suite(limit: int) -> dict:
    """Score retrieval quality against labeled relevant chunks.

    Deterministic and offline: hybrid recall + rerank are local, so this
    measures precision@k, recall@k, hit rate, and MRR without any provider
    call. Reported in the same shape as the model suites.
    """
    from app.rag.compare import (
        hit_rate_at_k,
        precision_at_k,
        recall_at_k,
        reciprocal_rank,
    )
    from app.rag.service import retrieve

    cases = load_cases("retrieval")[:limit]
    k = 3
    rows = []
    for case in cases:
        started = time.perf_counter()
        relevant = set(case["relevant_ids"])
        try:
            result = retrieve(case["query"], recall_k=10, final_k=k)
            retrieved = [s.chunk_id for s in result["sources"]]
            rows.append(
                {
                    "id": case["id"],
                    "retrieved": retrieved,
                    "precision": precision_at_k(retrieved, relevant, k),
                    "recall": recall_at_k(retrieved, relevant, k),
                    "hit": hit_rate_at_k(retrieved, relevant, k),
                    "rr": reciprocal_rank(retrieved, relevant),
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                }
            )
        except Exception:  # noqa: BLE001 - retrieval failure is data
            rows.append(
                {
                    "id": case["id"],
                    "retrieved": [],
                    "precision": 0.0,
                    "recall": 0.0,
                    "hit": 0.0,
                    "rr": 0.0,
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                }
            )

    total = len(rows)

    def mean(key: str) -> float:
        return round(sum(r[key] for r in rows) / total, 4) if total else 0.0

    latencies = [r["latency_ms"] for r in rows]
    return {
        "suite": "retrieval",
        "total_cases": total,
        "evaluated_cases": total,
        "passed": sum(1 for r in rows if r["hit"] == 1.0),
        "model_failures": sum(1 for r in rows if r["hit"] != 1.0),
        "api_errors": 0,
        "accuracy": mean("hit"),
        "api_error_rate": 0.0,
        "structured_output_validity": None,
        "retrieval": {
            "precision_at_k": mean("precision"),
            "recall_at_k": mean("recall"),
            "hit_rate_at_k": mean("hit"),
            "mrr": mean("rr"),
            "k": k,
        },
        "latency_ms": {
            "average": round(sum(latencies) / total, 2) if total else None,
            "p50": percentile(latencies, 0.50),
            "p95": percentile(latencies, 0.95),
            "p99": percentile(latencies, 0.99),
        },
        "tokens": {"input": 0, "output": 0, "total": 0},
        "cost": {"total_usd": 0.0, "average_per_request_usd": 0.0},
    }


async def run_suites(suites: list[str], limit: int) -> dict:
    """Run several suites and aggregate into a single report."""
    reports = []
    for suite in suites:
        if suite == "retrieval":
            reports.append(run_retrieval_suite(limit))
        else:
            reports.append(await run_suite(suite, limit))
    total_cases = sum(r["total_cases"] for r in reports)
    passed = sum(r["passed"] for r in reports)
    evaluated = sum(r["evaluated_cases"] for r in reports)
    api_errors = sum(r["api_errors"] for r in reports)
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "suites": reports,
        "totals": {
            "total_cases": total_cases,
            "evaluated_cases": evaluated,
            "passed": passed,
            "accuracy": round(passed / evaluated, 4) if evaluated else None,
            "api_errors": api_errors,
            "tokens": {
                "input": sum(r["tokens"]["input"] for r in reports),
                "output": sum(r["tokens"]["output"] for r in reports),
                "total": sum(r["tokens"]["total"] for r in reports),
            },
            "cost": {
                "total_usd": round(sum(r["cost"]["total_usd"] for r in reports), 6),
            },
        },
    }
