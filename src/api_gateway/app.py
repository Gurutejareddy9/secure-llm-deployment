"""FastAPI application entry point for the Secure LLM Gateway."""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from prometheus_client import make_asgi_app
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.api_gateway.middleware import RequestLoggingMiddleware
from src.api_gateway.routes import router
from src.monitoring.metrics import (
    CACHE_HITS,
    COST_TOTAL,
    REQUEST_COUNTER,
    SECURITY_BLOCKS,
    TOKENS_USED,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------
RATE_LIMIT = os.getenv("RATE_LIMIT_PER_MINUTE", "60")
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{RATE_LIMIT}/minute"])

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance.
    """
    app = FastAPI(
        title="Secure LLM Deployment API",
        description=(
            "A production-ready gateway for Large Language Models with "
            "JWT auth, prompt injection detection, PII filtering, semantic "
            "caching, and smart query routing."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS – tighten origin list in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Custom request logging / request-ID middleware
    app.add_middleware(RequestLoggingMiddleware)

    # Register API routes
    app.include_router(router)

    # Health-check endpoint (no auth required)
    @app.get("/health", tags=["ops"])
    async def health() -> dict:
        """Return service health status."""
        return {"status": "ok", "service": "secure-llm-deployment"}

    # Stats endpoint for dashboard (no auth — read-only counters)
    @app.get("/api/v1/stats", tags=["ops"])
    async def stats() -> dict:
        """Return aggregated metrics for the dashboard."""
        total = _counter_value(REQUEST_COUNTER)
        return {
            "total_requests": total,
            "cache_hits": _counter_value(CACHE_HITS),
            "security_blocks": _counter_value(SECURITY_BLOCKS),
            "total_cost": _counter_value(COST_TOTAL),
            "total_tokens": _counter_value(TOKENS_USED),
        }

    # Dashboard UI
    @app.get("/", tags=["ui"])
    async def dashboard():
        """Serve the single-page dashboard."""
        return FileResponse(STATIC_DIR / "dashboard.html")

    # Mount Prometheus metrics endpoint
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    return app


def _counter_value(metric) -> float:
    """Sum all label combinations of a Prometheus counter/gauge."""
    total = 0.0
    for sample in metric.collect()[0].samples:
        if sample.name.endswith("_total") or sample.name == metric._name:
            total += sample.value
    return total


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api_gateway.app:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8000")),
        reload=os.getenv("APP_DEBUG", "false").lower() == "true",
    )
