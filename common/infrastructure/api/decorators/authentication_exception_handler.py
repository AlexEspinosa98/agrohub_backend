"""
Authentication exception handler decorator for FastAPI endpoints.
"""

import functools
import logging
from typing import Any, Callable, TypeVar

from fastapi import HTTPException, status
from sqlalchemy import exc

from common.domain import exceptions as common_exceptions
from common.infrastructure.logging.config import get_logger


T = TypeVar("T")
_LOGGER: logging.Logger = get_logger(__name__)


def handle_authentication_exceptions(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to handle authentication exceptions in FastAPI endpoints.

    This decorator specifically handles:
    1. Token validation errors (empty, expired, invalid signature)
    2. Token decoding errors (payload, format issues)
    3. User validation errors (not found, inactive)

    Use this decorator ONLY on endpoints that require authentication.
    Combine with @handle_exceptions for complete error handling.

    Example:
        @router.post("/protected-endpoint")
        @handle_exceptions      # General exceptions
        @handle_auth_exceptions # Authentication exceptions
        def protected_endpoint(user: User = Depends(get_current_user)):
            pass

    Args:
        func: The function to decorate

    Returns:
        Callable: The decorated function with authentication error handling
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return func(*args, **kwargs)

        # Token Expired (401 Unauthorized)
        except common_exceptions.TokenExpiredException:
            _LOGGER.warning("Authentication failed - Token expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Token has expired",
                    "error_code": "TOKEN_EXPIRED",
                },
            )

        # Invalid Token Signature (401 Unauthorized)
        except common_exceptions.TokenSignatureException:
            _LOGGER.warning("Authentication failed - Invalid token signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Invalid token signature",
                    "error_code": "INVALID_TOKEN_SIGNATURE",
                },
            )

        # Token Payload Issues (401 Unauthorized)
        except common_exceptions.TokenPayloadException as e:
            _LOGGER.warning(
                f"Authentication failed - Invalid token payload: [{e.field}]"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": f"Invalid token payload - [{e.field}]: [{e.reason}]",
                    "error_code": "INVALID_TOKEN_PAYLOAD",
                    "field": e.field,
                },
            )

        # Token Decoding Issues (401 Unauthorized)
        except common_exceptions.TokenDecodingException as e:
            _LOGGER.warning(
                f"Authentication failed - Token decoding error: [{e.reason}]"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": f"Token decoding failed: [{e.reason}]",
                    "error_code": "TOKEN_DECODING_FAILED",
                },
            )

        # Invalid Token (401 Unauthorized)
        except common_exceptions.InvalidTokenException as e:
            _LOGGER.warning(f"Authentication failed - Invalid token: [{str(e)}]")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Invalid token provided",
                    "error_code": "INVALID_TOKEN",
                    "details": str(e),
                },
            )

        # Active User Not Found (404 Not Found)
        except common_exceptions.UserNotFoundException as e:
            _LOGGER.warning(
                f"Authentication failed - Active user [{e.user_id}] not found"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": f"Active user with ID [{e.user_id}] does not exist",
                    "error_code": "ACTIVE_USER_NOT_FOUND",
                    "user_id": e.user_id,
                },
            )

        except common_exceptions.InvalidUserStatusException as e:
            _LOGGER.warning(f"Invalid user status for authentication: [{str(e)}]")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": str(e),
                    "error_code": "INVALID_USER_STATUS",
                    "details": e.details if hasattr(e, "details") else {},
                },
            )

        # User Not Premium (403 Forbidden)
        except common_exceptions.UserNotPremiumException as e:
            _LOGGER.warning(f"User not premium: [{str(e)}]")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": str(e),
                    "error_code": "USER_NOT_PREMIUM",
                },
            )

        # User Not Active (401 Unauthorized)
        except common_exceptions.UserNotActiveException as e:
            _LOGGER.warning(f"User not active: [{str(e)}]")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": str(e),
                    "error_code": "USER_NOT_ACTIVE",
                },
            )

        # General Authentication Error (401 Unauthorized)
        except common_exceptions.AuthenticationException as e:
            _LOGGER.warning(f"General authentication error: [{str(e)}]")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": str(e),
                    "error_code": "AUTHENTICATION_FAILED",
                },
            )

        # SQLAlchemy Database Exceptions
        except exc.ProgrammingError as e:
            _LOGGER.error(f"Database programming error: [{str(e)}]")

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "message": "Database query error. Please contact support.",
                    "error_code": "DATABASE_QUERY_ERROR",
                },
            )

        except exc.IntegrityError as e:
            _LOGGER.error(f"Database integrity error: [{str(e)}]")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Data integrity violation. Please check your input.",
                    "error_code": "DATA_INTEGRITY_ERROR",
                },
            )

        except exc.OperationalError as e:
            _LOGGER.error(f"Database operational error: [{str(e)}]")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "message": "Database temporarily unavailable. Please try again later.",
                    "error_code": "DATABASE_UNAVAILABLE",
                },
            )

        except exc.DatabaseError as e:
            _LOGGER.error(f"General database error: [{str(e)}]")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "message": "Database error occurred. Please contact support.",
                    "error_code": "DATABASE_ERROR",
                },
            )

        except exc.SQLAlchemyError as e:
            _LOGGER.error(f"SQLAlchemy error: [{str(e)}]")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "message": "Database operation failed. Please contact support.",
                    "error_code": "SQLALCHEMY_ERROR",
                },
            )

    return wrapper
