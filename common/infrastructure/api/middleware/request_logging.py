"""
FastAPI implementation of the request logging middleware.
"""

import logging
import time
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Implementation of the request logging middleware."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        start_time: float = time.time()

        logger: logging.Logger = logging.getLogger("api")
        logger.info(
            "Request started",
            extra={
                "request_id": request.headers.get("X-Request-ID", "unknown"),
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown"),
            },
        )

        try:
            response: Response = await call_next(request)
            process_time: float = time.time() - start_time

            logger.info(
                "Request completed",
                extra={
                    "request_id": request.headers.get("X-Request-ID", "unknown"),
                    "status_code": response.status_code,
                    "process_time_ms": round(process_time * 1000, 2),
                },
            )
            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                "Request failed",
                extra={
                    "request_id": request.headers.get("X-Request-ID", "unknown"),
                    "error": str(e),
                    "process_time_ms": round(process_time * 1000, 2),
                },
                exc_info=True,
            )
            raise
