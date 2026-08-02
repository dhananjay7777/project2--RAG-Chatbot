"""Simple in-memory per-IP rate limiter for POST /ask."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


class PerIpRateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding 1-hour window; process-local (fine for a single Railway instance)."""

    def __init__(
        self,
        app,
        *,
        max_per_hour: int = 30,
        path: str = "/ask",
        window_seconds: int = 3600,
    ) -> None:
        super().__init__(app)
        self.max_per_hour = max_per_hour
        self.path = path
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method == "POST" and request.url.path.rstrip("/") == self.path.rstrip("/"):
            ip = client_ip(request)
            now = time.monotonic()
            bucket = self._hits[ip]
            cutoff = now - self.window_seconds
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_per_hour:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": (
                            "Rate limit exceeded. Try again later "
                            f"(limit {self.max_per_hour} questions per hour per IP)."
                        )
                    },
                )
            bucket.append(now)
        return await call_next(request)
