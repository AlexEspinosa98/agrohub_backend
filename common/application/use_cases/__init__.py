"""
Barrel exports for common application use cases.

Provides centralized import for all common use cases.
Usage: from common.application import use_cases as common_use_cases
"""

from .authenticate_user import AuthenticateUserUseCase


__all__: list[str] = [
    "AuthenticateUserUseCase",
]
