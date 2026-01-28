from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from common.domain import entities as common_entities
from common.infrastructure.database import models as common_database_models


EntityType = TypeVar("EntityType", bound=common_entities.BaseEntity)
ModelType = TypeVar("ModelType", bound=common_database_models.BaseModel)


class BaseRepository(ABC, Generic[EntityType]):
    """
    Base repository interface defining common operations for all domain repositories.

    This ensures consistency across all repositories and provides a contract
    that infrastructure implementations must follow.
    """

    @abstractmethod
    def save(self, entity: EntityType) -> EntityType:
        """Save an entity and return the saved version."""

    @abstractmethod
    def get_by_id(self, entity_id: int) -> EntityType | None:
        """Find an entity by its ID."""

    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """Delete an entity by ID. Returns True if deleted."""

    @abstractmethod
    def list_all(self) -> list[EntityType]:
        """List all entities with optional pagination."""
