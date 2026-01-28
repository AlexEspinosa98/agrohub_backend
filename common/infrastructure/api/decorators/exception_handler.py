"""
General error handler decorator for FastAPI endpoints.
"""

import functools
import logging
from typing import Any, Callable, TypeVar

from fastapi import HTTPException, status
from pydantic import ValidationError

from common.infrastructure.logging.config import get_logger


T = TypeVar("T")
_LOGGER: logging.Logger = get_logger(__name__)


def handle_exceptions(func: Callable[..., T]) -> Callable[..., T]:
    """
    General decorator to handle common exceptions in FastAPI endpoints.

    This decorator handles:
    1. Validation exceptions (input validation)
    2. General domain exceptions (business logic violations)
    3. Unexpected exceptions (500 errors)

    Args:
        func: The function to decorate

    Returns:
        Callable: The decorated function with general error handling
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return func(*args, **kwargs)

        except ValidationError as e:
            _LOGGER.error(f"Pydantic validation error: [{e}]")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "Input validation failed",
                    "error_code": "VALIDATION_ERROR",
                    "field_errors": e.errors(),
                },
            )
        except ValueError as e:
            _LOGGER.error(f"Value error: [{str(e)}]")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "Invalid input value",
                    "error_code": "VALUE_ERROR",
                    "details": str(e),
                },
            )

    return wrapper
