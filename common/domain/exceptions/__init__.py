"""
Barrel exports for common domain exceptions.

Provides centralized import for all common exceptions.
Usage: from common.domain import exceptions as common_exceptions
"""

from .authentication_exceptions import (
    AuthenticationException,
    InvalidTokenException,
    InvalidUserStatusException,
    TokenDecodingException,
    TokenExpiredException,
    TokenPayloadException,
    TokenSignatureException,
    UserNotActiveException,
    UserNotFoundException,
    UserNotPremiumException,
)


# Re-export for easy access
__all__: list[str] = [
    # Authentication-related exceptions
    "AuthenticationException",
    "InvalidTokenException",
    "UserNotFoundException",
    "TokenExpiredException",
    "TokenSignatureException",
    "TokenDecodingException",
    "TokenPayloadException",
    "InvalidUserStatusException",
    "UserNotPremiumException",
    "UserNotActiveException",
]
