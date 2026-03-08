"""API route definitions for the LLM gateway."""

import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

from src.api_gateway.auth import authenticate_user, create_access_token, decode_access_token
from src.cache.response_cache import ResponseCache
from src.inference.engine import LLMEngine
from src.monitoring.logger import get_logger
from src.monitoring.metrics import (
    ACTIVE_REQUESTS,
    CACHE_HITS,
    REQUEST_COUNTER,
    REQUEST_DURATION,
    SECURITY_BLOCKS,
)
from src.routing.query_router import QueryRouter
from src.security.input_sanitizer import InputSanitizer
from src.security.output_filter import OutputFilter
from src.security.pii_filter import PIIFilter
from src.security.prompt_guard import PromptGuard

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/token")
logger = get_logger(__name__)

# Module-level singletons (lazily replaced in tests via dependency injection)
_sanitizer = InputSanitizer()
_prompt_guard = PromptGuard()
_pii_filter = PIIFilter()
_output_filter = OutputFilter()
_query_router = QueryRouter()
_cache = ResponseCache()
_engine = LLMEngine()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class QueryRequest(BaseModel):
    """Request body for the /query endpoint."""

    query: str
    context: Optional[str] = None


class QueryResponse(BaseModel):
    """Response body for the /query endpoint."""

    response: str
    model_used: str
    cached: bool
    tokens_used: int
    cost_usd: float


# ---------------------------------------------------------------------------
# Dependency: current user
# ---------------------------------------------------------------------------


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Validate JWT and return the current user.

    Args:
        token: Bearer token from the Authorization header.

    Returns:
        User payload dict.

    Raises:
        HTTPException: 401 if token is invalid or user is disabled.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    username: str = payload.get("sub", "")
    if not username:
        raise credentials_exception
    return {"username": username}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/api/v1/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Issue a JWT access token given valid credentials.

    Args:
        form_data: OAuth2 form containing *username* and *password*.

    Returns:
        JSON with ``access_token`` and ``token_type``.

    Raises:
        HTTPException: 401 if credentials are incorrect.
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": user["username"]})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/api/v1/query", response_model=QueryResponse)
async def query_llm(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user),
):
    """Process a user query through the full security and inference pipeline.

    Args:
        request: Query request containing the user's prompt.
        current_user: Authenticated user (injected by JWT dependency).

    Returns:
        LLM response with metadata (model used, cost, cache status).

    Raises:
        HTTPException: 400 if the input is blocked by security filters.
        HTTPException: 500 on unexpected inference errors.
    """
    ACTIVE_REQUESTS.inc()
    REQUEST_COUNTER.labels(endpoint="/api/v1/query", status="started").inc()

    start = time.perf_counter()
    try:
        # 1. Sanitize input
        clean_query = _sanitizer.sanitize(request.query)

        # 2. Prompt injection guard
        guard_result = _prompt_guard.check(clean_query)
        if not guard_result["safe"]:
            SECURITY_BLOCKS.labels(reason="prompt_injection").inc()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Query blocked: {guard_result['reason']}",
            )

        # 3. PII filter on input
        clean_query = _pii_filter.redact(clean_query)

        # 4. Cache lookup
        cached_response = await _cache.get(clean_query)
        if cached_response:
            CACHE_HITS.inc()
            REQUEST_COUNTER.labels(endpoint="/api/v1/query", status="cache_hit").inc()
            return QueryResponse(
                response=cached_response["response"],
                model_used=cached_response["model_used"],
                cached=True,
                tokens_used=cached_response.get("tokens_used", 0),
                cost_usd=0.0,
            )

        # 5. Route query to appropriate model
        route = _query_router.route(clean_query)

        # 6. Run inference
        result = await _engine.infer(clean_query, model=route["model"])

        # 7. Filter output
        safe_output = _output_filter.filter(result["response"])

        # 8. Redact PII from output
        safe_output = _pii_filter.redact(safe_output)

        # 9. Store in cache
        await _cache.set(
            clean_query,
            {
                "response": safe_output,
                "model_used": route["model"],
                "tokens_used": result.get("tokens_used", 0),
            },
        )

        elapsed = time.perf_counter() - start
        REQUEST_DURATION.labels(model=route["model"]).observe(elapsed)
        REQUEST_COUNTER.labels(endpoint="/api/v1/query", status="success").inc()

        return QueryResponse(
            response=safe_output,
            model_used=route["model"],
            cached=False,
            tokens_used=result.get("tokens_used", 0),
            cost_usd=result.get("cost_usd", 0.0),
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("Inference error", error=str(exc))
        REQUEST_COUNTER.labels(endpoint="/api/v1/query", status="error").inc()
        raise HTTPException(status_code=500, detail="Internal inference error") from exc
    finally:
        ACTIVE_REQUESTS.dec()
