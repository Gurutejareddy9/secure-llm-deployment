"""CORS, rate-limiting, and request-logging middleware."""

import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request and log timing."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process a request, add an X-Request-ID header, and log timing.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware / handler in the chain.

        Returns:
            HTTP response with X-Request-ID and X-Process-Time headers added.
        """
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.perf_counter()
        response: Response = await call_next(request)
        process_time = time.perf_counter() - start_time

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.4f}s"
        return response
