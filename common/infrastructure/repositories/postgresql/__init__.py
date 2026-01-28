"""
Barrel exports for common PostgreSQL repositories.

Provides centralized import for all common PostgreSQL repositories.
Usage: from common.infrastructure.repositories import postgresql as common_pg_repos
"""

# First, import the base repository
from .base_repository import BasePostgreSQLRepository

# Then, import the specific repositories
from .authentication_repository import PostgreSQLAuthenticationRepository


# Re-export for easy access
__all__: list[str] = [
    "BasePostgreSQLRepository",
    "PostgreSQLAuthenticationRepository",
]
