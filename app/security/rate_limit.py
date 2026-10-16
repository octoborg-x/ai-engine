import os
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request


class InMemoryRateLimiter:
    """Small process-local fixed-window limiter suitable for the learning API."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> tuple[int, int]:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= self.limit:
                retry_after = max(1, int(self.window_seconds - (now - hits[0])))
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded; try again later",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)
            return self.limit - len(hits), self.window_seconds


def _setting(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


# The default budget is sized for an interactive console session: the web app
# issues one protected call per panel mounted, so a single visit spans several
# requests. The env var override still lets deployments tighten it behind a
# public edge if the API is ever exposed beyond the console.
rate_limiter = InMemoryRateLimiter(
    limit=_setting("RATE_LIMIT_REQUESTS", 120),
    window_seconds=_setting("RATE_LIMIT_WINDOW_SECONDS", 60),
)


def client_key(request: Request) -> str:
    """Use the direct peer address; do not trust spoofable forwarding headers."""
    return request.client.host if request.client else "unknown"
