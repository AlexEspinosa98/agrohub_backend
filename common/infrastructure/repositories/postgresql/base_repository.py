from abc import ABC, abstractmethod
from datetime import datetime
from typing import Generic, Sequence, Tuple, Type, TypeVar

from sqlalchemy import Result, Select, select
from sqlalchemy.orm import Session

from common.domain import (
    entities as common_entities,
    repositories as common_repositories,
)
from common.infrastructure.database import models as common_database_models


EntityType = TypeVar("EntityType", bound=common_entities.BaseEntity)
ModelType = TypeVar("ModelType", bound=common_database_models.BaseModel)


class BasePostgreSQLRepository(
    common_repositories.BaseRepository[EntityType], ABC, Generic[EntityType, ModelType]
):
    """
    Base PostgreSQL repository implementation using modern SQLAlchemy 2.0+ style.

    Uses select() statements for better type hints and future compatibility.
    """

    def __init__(self, session: Session, model_class: Type[ModelType]) -> None:
        self._session: Session = session
        self._model_class: type[ModelType] = model_class

    def save(self, entity: EntityType) -> EntityType:
        """Save entity to database."""
        if entity.is_persisted():
            # Update existing entity
            stmt: Select[Tuple[ModelType]] = select(self._model_class).where(
                self._model_class.id == entity.get_identity()
            )
            result: Result[Tuple[ModelType]] = self._session.execute(stmt)
            model: ModelType | None = result.scalar_one_or_none()

            if model:
                self._update_model_from_entity(model=model, entity=entity)
            else:
                model = self._to_database_model(entity=entity)
                self._session.add(model)
        else:
            # Create new entity
            model = self._to_database_model(entity)
            self._session.add(model)

        self._session.flush()  # Get the ID without committing
        return self._to_domain_entity(model=model)

    def get_by_id(self, entity_id: int) -> EntityType | None:
        """Find entity by ID using modern select() style."""
        stmt: Select[Tuple[ModelType]] = select(self._model_class).where(
            self._model_class.id == entity_id
        )
        result: Result[Tuple[ModelType]] = self._session.execute(stmt)
        model: ModelType | None = result.scalar_one_or_none()

        if not model:
            return None

        return self._to_domain_entity(model=model)

    def delete(self, entity_id: int) -> bool:
        """Soft delete - mark as inactive."""
        stmt: Select[Tuple[ModelType]] = select(self._model_class).where(
            self._model_class.id == entity_id
        )
        result: Result[Tuple[ModelType]] = self._session.execute(stmt)
        model: ModelType | None = result.scalar_one_or_none()

        if not model:
            return False
        model.is_active = False
        model.deleted_at = datetime.now()

        self._session.commit()
        return True

    def list_all(self) -> list[EntityType]:
        stmt: Select[Tuple[ModelType]] = select(self._model_class)
        result: Result[Tuple[ModelType]] = self._session.execute(stmt)
        models: Sequence[ModelType] = result.scalars().all()
        return [self._to_domain_entity(model=model) for model in models]

    def _update_model_from_entity(self, model: ModelType, entity: EntityType) -> None:
        """Update database model with entity data."""
        # Default implementation - subclasses can override
        new_model: ModelType = self._to_database_model(entity=entity)
        for key, value in new_model.__dict__.items():
            if not key.startswith("_") and hasattr(model, key) and key != "id":
                setattr(model, key, value)

    @abstractmethod
    def _to_domain_entity(self, model: ModelType) -> EntityType:
        """Convert database model to domain entity."""

    @abstractmethod
    def _to_database_model(self, entity: EntityType) -> ModelType:
        """Convert domain entity to database model."""
