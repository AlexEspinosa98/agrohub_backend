"""
Barrel exports for common domain value objects.

Provides centralized import for all common value objects.
Usage: from common.domain import value_objects as common_value_objects
"""

# First, import the base value object class
from .base import BaseValueObject


print("Importing common domain value objects...")
# Then, import specific value objects as needed
from .authentication_token import AuthenticationToken
from .pagination import PaginatedResult


__all__: list[str] = [
    # Base value object for inheritance
    "BaseValueObject",
    # Authentication-related value objects
    "AuthenticationToken",
    # Pagination-related value objects
    "PaginatedResult",
]
