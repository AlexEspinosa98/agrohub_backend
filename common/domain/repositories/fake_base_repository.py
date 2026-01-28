from datetime import datetime
from typing import Generic, Optional, TypeVar

from common.domain import (
    entities as common_entities,
    repositories as common_repositories,
)


EntityType = TypeVar("EntityType", bound=common_entities.BaseEntity)


class FakeBaseRepository(
    common_repositories.BaseRepository[EntityType], Generic[EntityType]
):
    """
    In-memory implementation of the BaseRepository for testing purposes.
    This repository stores entities in memory and provides all the required CRUD operations.
    """

    def __init__(self) -> None:
        """Initialize the repository with an empty list of entities."""
        self._entities: list[EntityType] = []

    def save(self, entity: EntityType) -> EntityType:
        """
        Save an entity to the in-memory store.

        Args:
            entity: The entity to save

        Returns:
            The saved entity
        """
        # If the entity has an ID, update it
        if entity.is_persisted():
            # Find and update existing entity
            for i, existing_entity in enumerate(self._entities):
                if existing_entity.get_identity() == entity.get_identity():
                    entity.mark_as_updated()
                    self._entities[i] = entity
                    return entity

            # If not found but has ID, add as new
            entity.mark_as_updated()
            self._entities.append(entity)
            return entity

        # If no ID, create a new one
        new_id: int = (
            max(
                [
                    existing_entity.get_identity()
                    for existing_entity in self._entities
                    if existing_entity.is_persisted()
                ],
                default=0,
            )
            + 1
        )

        entity.id = new_id

        entity.created_at = datetime.now()
        entity.updated_at = datetime.now()
        self._entities.append(entity)
        return entity

    def get_by_id(self, entity_id: int) -> Optional[EntityType]:
        """
        Get an entity by its ID.

        Args:
            entity_id: The ID of the entity to retrieve

        Returns:
            The entity if found, None otherwise
        """
        for entity in self._entities:
            if entity.is_persisted() and entity.get_identity() == entity_id:
                return entity
        return None

    def list_all(self) -> list[EntityType]:
        """
        List all active entities.

        Returns:
            List of all active entities
        """
        return [entity for entity in self._entities if entity.is_active]

    def delete(self, entity_id: int) -> bool:
        """
        Soft delete an entity by its ID.

        Args:
            entity_id: The ID of the entity to delete

        Returns:
            True if deleted, False if not found
        """
        for entity in self._entities:
            if entity.is_persisted() and entity.get_identity() == entity_id:
                entity.is_active = False
                entity.deleted_at = datetime.now()
                return True
        return False

    def add_test_data(self, entities: list[EntityType]) -> None:
        """
        Add test data to the repository.
        This is a helper method for testing purposes.

        Args:
            entities: List of entities to add
        """
        self._entities.extend(entities)
