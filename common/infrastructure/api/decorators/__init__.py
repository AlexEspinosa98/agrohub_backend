"""
Barrel exports for common API decorators.

Provides centralized import for all common API decorators.
Usage: from common.infrastructure.api import decorators as common_decorators
"""

from .authentication_exception_handler import handle_authentication_exceptions
from .exception_handler import handle_exceptions


__all__: list[str] = [
    "handle_authentication_exceptions",
    "handle_exceptions",
]
