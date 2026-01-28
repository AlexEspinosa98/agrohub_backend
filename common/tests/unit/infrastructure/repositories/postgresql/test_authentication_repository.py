"""
Unit tests for PostgreSQLAuthenticationRepository.

Tests authentication repository specific logic.
"""

import pytest
from sqlalchemy.orm import Session

from common.domain import (
    entities as common_entities,
    enums as common_enums,
)
from common.infrastructure.database import models as common_database_models
from common.infrastructure.repositories import postgresql
from common.tests.unit.domain.entities import builders as common_entities_builders
from common.tests.unit.infrastructure.database import (
    builders as common_database_builders,
)


class TestPostgreSQLAuthenticationRepository:
    """Test cases for PostgreSQLAuthenticationRepository."""

    @pytest.fixture
    def repository(
        self, session: Session
    ) -> postgresql.PostgreSQLAuthenticationRepository:
        """Fixture to create a PostgreSQLAuthenticationRepository instance."""
        return postgresql.PostgreSQLAuthenticationRepository(session=session)

    def test_find_active_user_by_id_existing_active_user(
        self,
        repository: postgresql.PostgreSQLAuthenticationRepository,
        session: Session,
    ) -> None:
        """Test finding an existing active user by ID."""

        # Create a user model using builder
        user_model: common_database_models.UserModel = (
            common_database_builders.UserModelMotherBuilder.active_user()
        )
        session.add(user_model)
        session.flush()

        user_id = 123

        # Act
        result: common_entities.AuthenticatedUser | None = (
            repository.find_active_user_by_id(user_id)
        )

        # Assert
        assert result.id == 123
        assert result.email == "test@example.com"
        assert result.user_status == common_enums.UserStatus.ACTIVE.value
        assert result.is_user_active is True
        assert result.is_active is True
        assert result.created_at == user_model.created_at
        assert result.updated_at == user_model.updated_at
        assert result.last_login == user_model.last_login

    def test_find_active_user_by_id_non_existing_user(
        self, repository: postgresql.PostgreSQLAuthenticationRepository
    ) -> None:
        """Test finding a non-existing user by ID."""
        # Arrange
        user_id = 999

        # Act
        result: common_entities.AuthenticatedUser | None = (
            repository.find_active_user_by_id(user_id)
        )

        # Assert
        assert result is None

    def test_find_active_user_by_id_inactive_user(
        self,
        session: Session,
        repository: postgresql.PostgreSQLAuthenticationRepository,
    ) -> None:
        """Test finding an inactive user by ID returns None."""

        # Create an inactive user using builder
        user_model: common_database_models.UserModel = (
            common_database_builders.UserModelMotherBuilder.inactive_user()
        )
        session.add(user_model)
        session.flush()

        user_id = 123

        # Act
        result: common_entities.AuthenticatedUser | None = (
            repository.find_active_user_by_id(user_id)
        )

        # Assert
        assert result is None  # Should not find inactive users

    def test_to_domain_entity_conversion(
        self,
        repository: postgresql.PostgreSQLAuthenticationRepository,
        session: Session,
    ) -> None:
        """Test conversion from database model to domain entity."""
        # Arrange
        user_model: common_database_models.UserModel = (
            common_database_builders.UserModelMotherBuilder.active_user()
        )

        # Act
        entity: common_entities.AuthenticatedUser = repository._to_domain_entity(
            model=user_model
        )

        # Assert
        assert isinstance(entity, common_entities.AuthenticatedUser)
        assert entity.email == "test@example.com"
        assert entity.user_status == common_enums.UserStatus.ACTIVE.value
        assert entity.id == user_model.id
        assert entity.is_user_active is True
        assert entity.is_active is True
        assert entity.created_at == user_model.created_at
        assert entity.updated_at == user_model.updated_at
        assert entity.last_login == user_model.last_login

    def test_to_database_model_raises_not_implemented(
        self, repository: postgresql.PostgreSQLAuthenticationRepository
    ) -> None:
        """Test that _to_database_model raises NotImplementedError."""
        # Arrange
        entity: common_entities.AuthenticatedUser = (
            common_entities_builders.AuthenticatedUserMotherBuilder.active_user()
        )

        # Act & Assert
        with pytest.raises(
            NotImplementedError, match="Cannot convert AuthenticatedUser"
        ):
            repository._to_database_model(entity=entity)
