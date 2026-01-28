from abc import ABC, abstractmethod

from common.domain import (
    entities as common_entities,
    repositories as common_repositories,
)


class AuthenticationRepository(
    common_repositories.BaseRepository[common_entities.AuthenticatedUser], ABC
):
    """
    Repository interface for AUTHENTICATION-specific operations.

    This is different from UserRepository which handles CRUD operations.
    This repository is focused only on authentication concerns.
    """

    @abstractmethod
    def find_active_user_by_id(
        self, user_id: int
    ) -> common_entities.AuthenticatedUser | None:
        """
        Find active user for authentication by ID.

        Returns None if user is not found or not active.
        """
