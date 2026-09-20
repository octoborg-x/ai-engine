import logging
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from openai import APIError, APITimeoutError, RateLimitError
from pydantic import BaseModel

from app.llm.client import ask, ask_stream, extract_ticket_info
from app.llm.schemas import ChatRequest, ChatResponse, TicketExtraction
from app.rag.schemas import AskRequest, AskResponse
from app.rag.service import answer
from app.security.auth import authenticate
from app.security.rate_limit import client_key, rate_limiter
from app.telemetry.logging import (
    clear_request_context,
    configure_logging,
    get_request_id,
    get_trace_id,
    set_request_context,
)

configure_logging()
logger = logging.getLogger("app.request")
app = FastAPI(title="AI API Project")


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    tokens = set_request_context(
        request.headers.get("x-request-id"),
        request.headers.get("x-trace-id"),
    )
    started = time.perf_counter()
    status = "success"
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
        clear_request_context(tokens)


@app.middleware("http")
async def api_security_middleware(request: Request, call_next):
    """Enforce rate limit -> authentication -> validation -> LLM."""
    if request.url.path in ["/chat", "/ask"] and request.method == "POST":
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


@app.get("/health")
def health():
    return {"status": "ok"}


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
        result = await ask(req.prompt)
        return ChatResponse(**result)
    except Exception as e:
        raise _provider_error(e) from e


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
        ask_stream(req.prompt),
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
