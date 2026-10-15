from typing import Literal

from pydantic import BaseModel


class ChatRequest(BaseModel):
    prompt: str
    tier: Literal["cheap", "balanced", "powerful"] | None = None


class ChatResponse(BaseModel):
    response: str
    model: str
    route: Literal["cheap", "balanced", "powerful"]
    route_reason: str = ""
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: float
    latency_ms: float
    success: bool


class TicketExtraction(BaseModel):
    summary: str
    category: Literal["billing", "technical", "account", "other"]
    urgency: Literal["low", "medium", "high"]
    customer_sentiment: Literal["positive", "neutral", "negative"]
