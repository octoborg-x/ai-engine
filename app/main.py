import logging
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from openai import APIError, APITimeoutError, RateLimitError
from pydantic import BaseModel

from app.llm.client import ask, ask_stream, extract_ticket_info
from app.llm.schemas import ChatRequest, ChatResponse, TicketExtraction
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
        remaining, window = rate_limiter.check(client_key(request))
        authenticate(request)
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(window)
        return response
    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=ChatResponse)
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        result = await ask(req.prompt)
        return ChatResponse(**result)
    except RateLimitError as e:
        raise HTTPException(
            status_code=429, detail="Rate limited by provider, try again shortly"
        ) from e
    except APITimeoutError as e:
        raise HTTPException(status_code=504, detail="LLM provider timed out") from e
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"LLM provider error: {e!s}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e!s}") from e


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
