from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.infrastructure.db.session.factory import dispose_engine
from app.presentation.api.errors import register_error_handlers, register_http_error_handlers
from app.presentation.api.middleware import RateLimitMiddleware, RequestLoggingMiddleware
from app.presentation.api.rate_limit import SlidingWindowRateLimiter
from app.presentation.api.routers import analytics, auth, budgets, categories, debts, export, me, reminders, savings, transactions


@asynccontextmanager
async def _lifespan(_: FastAPI):
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET must be set to run the API")

    app = FastAPI(
        title="Wallet API", version="0.1.0", docs_url="/api/docs",
        openapi_url="/api/openapi.json", lifespan=_lifespan,
    )

    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_methods=["*"],
            allow_headers=["Authorization", "Content-Type"],
        )

    limiter = SlidingWindowRateLimiter(
        settings.rate_limit_requests, settings.rate_limit_window_seconds
    )
    app.add_middleware(RateLimitMiddleware, limiter=limiter, jwt_secret=settings.jwt_secret)
    # Logging is added last so it wraps rate limiting and CORS, and so it observes
    # every response, including a 429 from the rate limiter.
    app.add_middleware(RequestLoggingMiddleware)

    register_error_handlers(app)
    register_http_error_handlers(app)

    v1 = APIRouter(prefix="/api/v1")
    v1.include_router(auth.router)
    v1.include_router(me.router)
    v1.include_router(transactions.router)
    v1.include_router(categories.router)
    v1.include_router(budgets.router)
    v1.include_router(analytics.router)
    v1.include_router(debts.router)
    v1.include_router(savings.router)
    v1.include_router(reminders.router)
    v1.include_router(export.router)
    app.include_router(v1)

    @app.get("/health", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
