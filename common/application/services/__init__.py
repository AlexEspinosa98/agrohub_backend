"""
Barrel exports for common application services.

Provides centralized import for all common application services.
Usage: from common.application import services as common_services
"""

from .authentication_service import AuthenticationService


__all__: list[str] = [
    "AuthenticationService",
]
