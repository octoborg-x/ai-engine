from typing import Literal

from pydantic import BaseModel

# The selectable tiers. "main" is the active provider's chat model; the three
# routed tiers are cheap/balanced/powerful; "openai-compatible" always targets
# the OpenAI-compatible slot (OPENAI_API_KEY + OPENAI_BASE_URL + OPENAI_MODEL),
# independent of the active provider.
TierName = Literal["main", "cheap", "balanced", "powerful", "openai-compatible"]


class ChatRequest(BaseModel):
    prompt: str
    tier: TierName | None = None


class ChatResponse(BaseModel):
    response: str
    model: str
    route: TierName
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
