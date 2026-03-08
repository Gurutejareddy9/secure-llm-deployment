"""Structured JSON logger using structlog."""

import logging
import os
import sys
from typing import Any

import structlog

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# ---------------------------------------------------------------------------
# Configure standard library logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=getattr(logging, LOG_LEVEL, logging.INFO),
)

# ---------------------------------------------------------------------------
# Configure structlog
# ---------------------------------------------------------------------------
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)


def get_logger(name: str = "llm-gateway") -> Any:
    """Return a structlog logger bound to *name*.

    Args:
        name: Logger name (usually ``__name__``).

    Returns:
        Bound structlog logger instance.
    """
    return structlog.get_logger(name)


def log_security_event(event: str, **kwargs: Any) -> None:
    """Log a security-related event at WARNING level.

    Args:
        event: Short description of the security event.
        **kwargs: Additional context key-value pairs.
    """
    logger = get_logger("security")
    logger.warning(event, **kwargs)


def log_request(
    request_id: str,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    **kwargs: Any,
) -> None:
    """Log an HTTP request at INFO level.

    Args:
        request_id: Unique request identifier.
        method: HTTP method (GET, POST, …).
        path: Request path.
        status_code: HTTP response status code.
        duration_ms: Request processing time in milliseconds.
        **kwargs: Additional context key-value pairs.
    """
    logger = get_logger("access")
    logger.info(
        "http_request",
        request_id=request_id,
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=round(duration_ms, 2),
        **kwargs,
    )
