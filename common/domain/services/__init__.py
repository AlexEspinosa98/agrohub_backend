"""
Common domain services module.

Contains domain services that apply across multiple bounded contexts.
"""

from .user_validation_service import UserValidationService


__all__ = [
    "UserValidationService",
]
