import logging
import os
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from openai import APIError, APITimeoutError, RateLimitError
from pydantic import BaseModel

from app.llm.client import ask, ask_stream, extract_ticket_info
from app.llm.schemas import ChatRequest, ChatResponse, TicketExtraction
from app.rag.schemas import AskRequest, AskResponse, RetrievalResponse
from app.rag.service import answer, retrieval_response
from app.recruitment.screening import ScreeningReport, ScreenRequest, screen
from app.security.auth import authenticate
from app.security.rate_limit import client_key, rate_limiter
from app.telemetry.logging import (
    clear_request_context,
    configure_logging,
    get_request_id,
    get_trace_id,
    set_request_context,
)
from app.telemetry.metrics import MetricsCollector
from app.telemetry.records import recent_llm_calls, recent_requests, record_request

configure_logging()
logger = logging.getLogger("app.request")
app = FastAPI(title="AI API Project")

# Health/readiness probes stay public for deployment platforms. Every endpoint
# that can invoke AI work, enqueue work, expose job results, or reveal metrics is
# protected by the same bearer-token boundary and per-client rate limiter.
PROTECTED_ROUTES = {
    ("POST", "/chat"),
    ("POST", "/ask"),
    ("POST", "/chat/stream"),
    ("POST", "/extract-ticket"),
    ("POST", "/jobs"),
    ("GET", "/metrics"),
    ("GET", "/observability/requests"),
    ("GET", "/compare"),
    ("GET", "/evals/suites"),
    ("POST", "/evals/run"),
    ("GET", "/security/policy"),
    ("GET", "/models"),
    ("POST", "/rag/retrieve"),
    ("POST", "/recruitment/screen"),
}


def _requires_authentication(request: Request) -> bool:
    route = (request.method.upper(), request.url.path.rstrip("/") or "/")
    if route in PROTECTED_ROUTES:
        return True

    # Job IDs are dynamic paths, so protect reads without matching unrelated URLs.
    segments = request.url.path.strip("/").split("/")
    return (
        request.method.upper() == "GET"
        and len(segments) == 2
        and segments[0] == "jobs"
        and bool(segments[1])
    )


@app.middleware("http")
async def api_security_middleware(request: Request, call_next):
    """Apply abuse protection and authentication before protected operations."""
    if _requires_authentication(request):
        try:
            remaining, window = rate_limiter.check(client_key(request))
            authenticate(request)
        except HTTPException as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=exc.headers,
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(window)
        return response
    return await call_next(request)


@app.get("/")
def root():
    return {"status": "ok", "service": "ai-engine"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    tokens = set_request_context(
        request.headers.get("x-request-id"),
        request.headers.get("x-trace-id"),
    )
    started = time.perf_counter()
    status = "success"
    response = None
    try:
        logger.info(
            "request started",
            extra={"event": "request.start", "status": "started"},
        )
        response = await call_next(request)
        response.headers["x-request-id"] = get_request_id()
        response.headers["x-trace-id"] = get_trace_id()
        status = "success" if response.status_code < 500 else "error"
        return response
    except Exception:
        status = "error"
        raise
    finally:
        logger.info(
            "request completed",
            extra={
                "event": "request.end",
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "status": status,
            },
        )
        status_code = (
            response.status_code
            if response is not None
            else (500 if status == "error" else 200)
        )
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        MetricsCollector.record_http(
            request.method,
            request.url.path,
            status_code,
            latency_ms,
        )
        record_request(request.method, request.url.path, status_code, latency_ms)
        clear_request_context(tokens)


@app.get("/metrics")
def metrics_endpoint():
    return MetricsCollector.snapshot()


@app.get("/observability/requests")
def observability_requests(limit: int = 50):
    """Recent request and LLM-call records with correlation IDs.

    Metadata only: no prompt or completion content is stored or returned.
    """
    bounded = max(1, min(limit, 200))
    return {
        "requests": recent_requests(bounded),
        "llm_calls": recent_llm_calls(bounded),
    }


@app.get("/ready")
def ready():
    if os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY"):
        return {"status": "ready"}
    return JSONResponse(
        status_code=503,
        content={
            "status": "not ready",
            "detail": "OPENROUTER_API_KEY or OPENAI_API_KEY missing",
        },
    )


def _provider_error(e: Exception) -> HTTPException:
    """Map LLM provider failures onto the documented HTTP status codes."""
    if isinstance(e, RateLimitError):
        return HTTPException(
            status_code=429, detail="Rate limited by provider, try again shortly"
        )
    if isinstance(e, APITimeoutError):
        return HTTPException(status_code=504, detail="LLM provider timed out")
    if isinstance(e, APIError):
        return HTTPException(status_code=502, detail=f"LLM provider error: {e!s}")
    return HTTPException(status_code=500, detail=f"Unexpected error: {e!s}")


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        result = await ask(req.prompt, tier=req.tier)
        return ChatResponse(**result)
    except Exception as e:
        raise _provider_error(e) from e


@app.post("/recruitment/screen", response_model=ScreeningReport)
async def recruitment_screen(req: ScreenRequest):
    """Screen one candidate against one job description, end to end."""
    try:
        return await screen(req)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise _provider_error(e) from e


@app.get("/compare")
async def compare(limit: int = 5):
    """Benchmark each routing tier over the same labeled prompt set."""
    from app.evals.compare import compare_tiers

    bounded = max(1, min(limit, 10))
    try:
        return await compare_tiers(bounded)
    except Exception as e:
        raise _provider_error(e) from e


@app.get("/evals/suites")
def eval_suites():
    """Index of available evaluation suites and their case counts."""
    from app.evals.engine import suite_sizes

    sizes = suite_sizes()
    return {
        "suites": [
            {"name": name, "cases": count, "file": f"{name}_cases.json"}
            for name, count in sizes.items()
        ]
    }


class EvalRunRequest(BaseModel):
    """Optional body for /evals/run; omitted fields fall back to defaults."""

    suites: list[str] | None = None
    limit: int = 5


@app.post("/evals/run")
async def evals_run(req: EvalRunRequest | None = None):
    """Run a bounded evaluation over the requested suites.

    Body: {"suites": ["chat","extraction",...], "limit": 5}. Results are
    measured against labeled cases; nothing is fabricated.
    """
    from app.evals.engine import SUITE_FILES, run_suites

    requested = (req.suites if req else None) or list(SUITE_FILES)
    suites = [s for s in requested if s in SUITE_FILES] or list(SUITE_FILES)
    limit = req.limit if req else 5
    bounded = max(1, min(limit, 10))
    try:
        return await run_suites(suites, bounded)
    except Exception as e:
        raise _provider_error(e) from e


@app.get("/models")
def models():
    """The routing tiers and the model each tier resolves to from the environment."""
    from app.llm.router import model_catalog

    return {"tiers": model_catalog()}


@app.post("/rag/retrieve", response_model=RetrievalResponse)
async def rag_retrieve(req: AskRequest):
    """Retrieval only: fused candidates, rerank scores, and citations.

    No LLM answer is generated, so this exposes the RAG workflow (hybrid
    recall -> rerank -> citations) without provider cost.
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    return retrieval_response(req.query, recall_k=req.recall_k, final_k=req.final_k)


@app.get("/security/policy")
def security_policy():
    """Non-secret facts about the auth and rate-limit boundary.

    Lets the console show the real enforced policy (and prove protected routes
    reject unauthenticated requests) without exposing any secret value.
    """
    return {
        "auth": {
            "scheme": "bearer",
            "enabled": bool(os.getenv("API_AUTH_TOKEN")),
            "header": "Authorization: Bearer <token>",
        },
        "rate_limit": {
            "limit": rate_limiter.limit,
            "window_seconds": rate_limiter.window_seconds,
            "key": "direct peer address (forwarding headers ignored)",
            "headers": ["X-RateLimit-Remaining", "X-RateLimit-Window", "Retry-After"],
        },
        "protected_routes": sorted(
            f"{method} {path}" for method, path in PROTECTED_ROUTES
        ),
        "public_routes": ["GET /health", "GET /ready", "GET /"],
    }


@app.post("/ask", response_model=AskResponse)
async def ask_endpoint(req: AskRequest):
    """Answer a question grounded in the retrieved knowledge-base context."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    try:
        return await answer(req.query, ask, recall_k=req.recall_k, final_k=req.final_k)
    except Exception as e:
        raise _provider_error(e) from e


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    return StreamingResponse(
        ask_stream(req.prompt, tier=req.tier),
        media_type="text/event-stream",
    )


class TicketRequest(BaseModel):
    message: str


@app.post("/extract-ticket", response_model=TicketExtraction)
async def extract_ticket(req: TicketRequest):
    try:
        return await extract_ticket_info(req.message)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


# Background jobs are isolated from the synchronous LLM endpoints above.
from app.jobs import router as jobs_router
from app.jobs import start_workers, stop_workers

app.include_router(jobs_router)


@app.on_event("startup")
async def startup_event():
    await start_workers()


@app.on_event("shutdown")
async def shutdown_event():
    await stop_workers()
