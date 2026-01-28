from typing import Optional

from common.domain import (
    entities as common_entities,
    repositories as common_repositories,
)


class FakeAuthenticationRepository(
    common_repositories.FakeBaseRepository[common_entities.AuthenticatedUser],
    common_repositories.AuthenticationRepository,
):
    """
    In-memory implementation of AuthenticationRepository for testing purposes.
    Inherits all CRUD operations from FakeBaseRepository and adds authentication-specific methods.
    """

    def find_active_user_by_id(
        self, user_id: int
    ) -> Optional[common_entities.AuthenticatedUser]:
        """
        Find active user for authentication by ID.

        Args:
            user_id: The ID of the user to find

        Returns:
            The authenticated user if found and active, None otherwise
        """
        for entity in self._entities:
            if (
                entity.is_persisted()
                and entity.get_identity() == user_id
                and entity.is_active
            ):
                return entity
        return None
