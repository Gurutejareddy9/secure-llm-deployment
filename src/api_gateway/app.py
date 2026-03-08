"""FastAPI application entry point for the Secure LLM Gateway."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.api_gateway.middleware import RequestLoggingMiddleware
from src.api_gateway.routes import router

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

    # Mount Prometheus metrics endpoint
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api_gateway.app:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8000")),
        reload=os.getenv("APP_DEBUG", "false").lower() == "true",
    )
