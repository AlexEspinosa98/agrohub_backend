from datetime import datetime

import pytest
from sqlalchemy import String
from sqlalchemy.orm import Mapped, Session, mapped_column

from common.domain import (
    entities as common_entities,
)
from common.infrastructure.database import models as common_database_models
from common.infrastructure.repositories import (
    postgresql as common_postgresql_repositories,
)


# Test entity for testing purposes
class TestEntity(common_entities.BaseEntity):
    """Test entity for repository testing."""

    name: str


# Test SQLAlchemy model for testing purposes
class TestModel(common_database_models.BaseModel):
    """Test SQLAlchemy model for repository testing."""

    __tablename__ = "test_entities"

    name: Mapped[str] = mapped_column(String, index=True, nullable=False)


# Concrete implementation for testing
class TestRepository(
    common_postgresql_repositories.BasePostgreSQLRepository[TestEntity, TestModel]
):
    """Concrete repository implementation for testing."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, TestModel)

    def _to_database_model(self, entity: TestEntity) -> TestModel:
        """Convert entity to model."""
        return TestModel(
            id=entity.id if entity.id else None,
            name=entity.name,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )

    def _to_domain_entity(self, model: TestModel) -> TestEntity:
        """Convert model to entity."""
        return TestEntity(
            id=model.id,
            name=model.name,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )


@pytest.fixture
def repository(
    session: Session,
) -> common_postgresql_repositories.BasePostgreSQLRepository:
    """Fixture to create a PostgreSQLAuthenticationRepository instance."""
    return TestRepository(session)


class TestBasePostgreSQLRepository:
    """Tests for the base PostgreSQL repository."""

    def test_save_new_entity(
        self, repository: common_postgresql_repositories.BasePostgreSQLRepository
    ) -> None:
        """Test saving a new entity to the database."""
        # Arrange
        entity = TestEntity(name="Test Entity", id=1)

        # Act
        saved_entity: TestEntity = repository.save(entity)

        # Assert
        assert saved_entity.id == 1  # ID should be set by the database
        assert saved_entity.name == "Test Entity"
        assert saved_entity.is_active is True
        assert type(saved_entity.created_at) is datetime
        assert type(saved_entity.updated_at) is datetime
        assert saved_entity.deleted_at is None

    def test_save_new_entity_without_id(
        self, repository: common_postgresql_repositories.BasePostgreSQLRepository
    ) -> None:
        """Test saving a new entity without ID (typical frontend scenario)."""
        # Arrange
        entity = TestEntity(name="Test Entity")  # New entity without id

        # Assert precondition
        assert entity.is_new_entity() is True
        assert entity.is_persisted() is False

        # Act
        saved_entity: TestEntity = repository.save(entity)

        # Assert
        assert saved_entity.id is not None  # ID should be set by the database
        assert saved_entity.is_persisted() is True
        assert saved_entity.name == "Test Entity"
        assert saved_entity.is_active is True

    def test_save_existing_entity_with_id(
        self, repository: common_postgresql_repositories.BasePostgreSQLRepository
    ) -> None:
        """Test saving an existing entity with ID (update scenario)."""
        # Arrange
        # First create and save
        new_entity = TestEntity(name="Original Name")
        saved_entity: TestEntity = repository.save(new_entity)

        # Modify the persisted entity
        saved_entity.name = "Updated Name"

        # Assert precondition
        assert saved_entity.is_persisted() is True

        # Act
        updated_entity: TestEntity = repository.save(saved_entity)

        # Assert
        assert updated_entity.id == saved_entity.id  # Same ID
        assert updated_entity.name == "Updated Name"

    def test_new_entity_get_identity_raises_error(self) -> None:
        """Test that getting identity of new entity raises error."""
        # Arrange
        entity = TestEntity(name="Test")

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot get identity of a new entity"):
            entity.get_identity()

    def test_get_by_id_existing(
        self, repository: common_postgresql_repositories.BasePostgreSQLRepository
    ) -> None:
        """Test retrieving an existing entity by ID."""
        # Arrange
        entity = TestEntity(name="Test Entity", id=1)
        saved_entity: TestEntity = repository.save(entity)

        # Act
        retrieved_entity: TestEntity | None = repository.get_by_id(
            saved_entity.get_identity()
        )

        # Assert
        assert retrieved_entity.id == saved_entity.id
        assert retrieved_entity.name == "Test Entity"
        assert retrieved_entity.is_active is True
        assert retrieved_entity.created_at == saved_entity.created_at
        assert retrieved_entity.updated_at == saved_entity.updated_at
        assert retrieved_entity.deleted_at is None

    def test_get_by_id_non_existing(
        self, repository: common_postgresql_repositories.BasePostgreSQLRepository
    ) -> None:
        """Test retrieving a non-existing entity by ID."""

        # Act
        result: TestEntity | None = repository.get_by_id(999)

        # Assert
        assert result is None

    def test_list_all_empty(
        self, repository: common_postgresql_repositories.BasePostgreSQLRepository
    ) -> None:
        """Test listing all entities when repository is empty."""
        # Act
        entities: list[TestEntity] = repository.list_all()

        # Assert
        assert entities == []
        assert isinstance(entities, list)

    def test_list_all_with_entities(
        self, repository: common_postgresql_repositories.BasePostgreSQLRepository
    ) -> None:
        """Test listing all entities when repository has data."""
        # Arrange
        entity1 = TestEntity(name="Entity 1", id=1)
        entity2 = TestEntity(name="Entity 2", id=2)

        repository.save(entity1)
        repository.save(entity2)

        # Act
        entities: list[TestEntity] = repository.list_all()

        # Assert
        assert len(entities) == 2
        assert all(isinstance(entity, TestEntity) for entity in entities)

        names: list[str] = [entity.name for entity in entities]
        assert "Entity 1" in names
        assert "Entity 2" in names

    def test_delete_existing_entity(
        self, repository: common_postgresql_repositories.BasePostgreSQLRepository
    ) -> None:
        """Test soft deleting an existing entity."""
        # Arrange
        entity = TestEntity(name="To be deleted", id=1)
        saved_entity: TestEntity = repository.save(entity)

        # Act
        result: bool = repository.delete(saved_entity.get_identity())

        # Assert
        assert result is True

        # Verify entity is soft deleted (marked as inactive)
        deleted_entity: TestEntity | None = repository.get_by_id(
            saved_entity.get_identity()
        )
        assert deleted_entity is not None  # Still exists in DB
        assert deleted_entity.is_active is False  # But marked as inactive
        assert deleted_entity.deleted_at is not None  # Deleted timestamp should be set
        assert (
            deleted_entity.deleted_at > saved_entity.created_at
        )  # Deleted after creation

    def test_delete_non_existing_entity(
        self, repository: common_postgresql_repositories.BasePostgreSQLRepository
    ) -> None:
        """Test deleting a non-existing entity."""
        # Act
        result: bool = repository.delete(999)

        # Assert
        assert result is False

    def test_to_database_model_conversion(
        self, repository: common_postgresql_repositories.BasePostgreSQLRepository
    ) -> None:
        """Test entity to database model conversion."""
        # Arrange
        entity = TestEntity(id=1, name="Test Entity")

        # Act
        model: TestModel = repository._to_database_model(entity)

        # Assert
        assert isinstance(model, TestModel)
        assert model.id == 1
        assert model.name == "Test Entity"
        assert model.is_active is True
        assert model.created_at == entity.created_at
        assert model.updated_at == entity.updated_at
        assert model.deleted_at is None

    def test_to_domain_entity_conversion(
        self, repository: common_postgresql_repositories.BasePostgreSQLRepository
    ) -> None:
        """Test model to domain entity conversion."""
        # Arrange
        model = TestModel(
            id=1,
            name="Test Entity",
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Act
        entity: TestEntity = repository._to_domain_entity(model)

        # Assert
        assert isinstance(entity, TestEntity)
        assert entity.id == 1
        assert entity.is_persisted() is True
        assert entity.is_new_entity() is False
        assert entity.name == "Test Entity"
        assert entity.is_active is True
        assert entity.created_at == model.created_at
        assert entity.updated_at == model.updated_at
        assert entity.deleted_at is None
