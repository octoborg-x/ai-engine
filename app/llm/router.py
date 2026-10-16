"""Free, deterministic model routing for OpenRouter.

The router deliberately does not make a second LLM call to decide which model
to use. It uses the request type and a small complexity heuristic, so routing
itself adds no token cost.
"""

import os
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RouteDecision:
    tier: str
    model: str
    reason: str


# "main" is the default model (MODEL_NAME); the other three are the routed
# tiers. Ordering here is the order the console renders.
TIERS = ("main", "cheap", "balanced", "powerful")


def _model_for(tier: str) -> str:
    # MODEL_NAME is the primary/default model, exposed as the "main" tier.
    if tier == "main":
        return os.environ["MODEL_NAME"]

    configured = os.getenv(f"MODEL_{tier.upper()}")
    if configured:
        return configured

    # Backward-compatible fallback: existing MODEL_NAME remains valid.
    return os.environ["MODEL_NAME"]


def model_catalog() -> list[dict]:
    """Describe each tier and the model actually resolved from the environment.

    Never returns secrets — only the tier, its env var name, and the model id.
    """
    catalog = []
    for tier in TIERS:
        env_var = "MODEL_NAME" if tier == "main" else f"MODEL_{tier.upper()}"
        try:
            model = _model_for(tier)
            configured = bool(os.getenv(env_var))
        except KeyError:
            model = "unconfigured"
            configured = False
        catalog.append(
            {
                "tier": tier,
                "env_var": env_var,
                "model": model,
                "configured": configured,
                "fallback": not configured and model != "unconfigured",
            }
        )
    return catalog


def route(task: str, prompt: str, force_tier: str | None = None) -> RouteDecision:
    """Select a free-model tier without an additional LLM request.

    Task mapping:
    - classification/extraction -> cheap
    - normal chat -> balanced
    - complex reasoning -> powerful

    When ``force_tier`` is one of the known tiers, that tier is used verbatim
    and the reason records that the caller pinned the route.
    """
    normalized_task = task.lower().strip()
    text = prompt.lower()

    if force_tier in TIERS:
        return RouteDecision(
            tier=force_tier,
            model=_model_for(force_tier),
            reason="tier pinned by request",
        )

    if normalized_task in {"classification", "extraction"}:
        tier = "cheap"
        reason = "structured classification/extraction task"
    else:
        complexity_markers = (
            "debug",
            "architecture",
            "system design",
            "compare",
            "trade-off",
            "tradeoff",
            "reason",
            "analyze",
            "analyse",
            "step by step",
            "complex",
            "code",
            "refactor",
        )
        long_prompt = len(text) >= 2500
        has_complexity_marker = any(
            re.search(rf"\b{re.escape(marker)}\b", text)
            for marker in complexity_markers
        )

        if long_prompt or has_complexity_marker:
            tier = "powerful"
            reason = "complexity heuristic matched"
        else:
            tier = "balanced"
            reason = "normal chat request"

    return RouteDecision(tier=tier, model=_model_for(tier), reason=reason)
