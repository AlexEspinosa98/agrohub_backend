"""
Common domain package.

Contains all domain layer components including entities, value objects,
aggregates, and shared domain logic.
"""

from .base_domain_object import BaseDomainObject


__all__: list[str] = [
    "BaseDomainObject",
]
