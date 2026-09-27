import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.presentation.api.auth.tokens import InvalidToken, decode_token
from app.presentation.api.errors import error_body
from app.presentation.api.rate_limit import SlidingWindowRateLimiter

logger = structlog.get_logger("wallet.api")


def _rate_limit_key(request: Request, jwt_secret: str) -> str:
    """The authenticated user id when the bearer token decodes, otherwise the client IP
    (covers /auth/telegram and requests with no/invalid token, so those can't be used
    to dodge the per-user limit)."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            return f"user:{decode_token(auth[7:], jwt_secret)}"
        except InvalidToken:
            pass
    client = request.client
    return f"ip:{client.host if client else 'unknown'}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limiter: SlidingWindowRateLimiter, jwt_secret: str) -> None:
        super().__init__(app)
        self._limiter = limiter
        self._jwt_secret = jwt_secret

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path == "/health":
            return await call_next(request)
        key = _rate_limit_key(request, self._jwt_secret)
        allowed, remaining, retry_after = self._limiter.check(key)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content=error_body("rate_limited", "Too many requests"),
                headers={"Retry-After": str(int(retry_after) + 1)},
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 1)
        user_id = getattr(request.state, "user_id", None)
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
            user_id=user_id,
        )
        return response
