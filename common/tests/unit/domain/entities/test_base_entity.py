"""
Unit tests for BaseEntity.

Tests base entity functionality specific to entities.
"""

from datetime import datetime
from typing import Any

import pytest

from common.domain import (
    entities as common_entities,
)


class TestEntity(common_entities.BaseEntity):
    """Test entity for base entity testing."""

    name: str
    value: int = 0


class TestBaseEntity:
    """Test cases for BaseEntity."""

    def test_base_entity_creation_with_required_id(self) -> None:
        """Test base entity creation with required positive ID."""
        # Act
        entity = TestEntity(name="test", id=1)

        # Assert
        assert entity.id == 1
        assert entity.name == "test"
        assert entity.value == 0
        assert entity.created_at is not None
        assert entity.updated_at is not None
        assert isinstance(entity.created_at, datetime)
        assert isinstance(entity.updated_at, datetime)
        assert entity.is_active is True
        assert entity.deleted_at is None

    def test_base_entity_id_validation_positive_only(self) -> None:
        """Test that entity ID must be positive."""
        # Act & Assert
        with pytest.raises(ValueError):
            TestEntity(name="test", id=0)  # Zero not allowed

        with pytest.raises(ValueError):
            TestEntity(name="test", id=-1)  # Negative not allowed

    def test_mark_as_updated_changes_timestamp(self) -> None:
        """Test mark_as_updated functionality updates timestamp."""
        # Arrange
        entity = TestEntity(name="test", id=1)
        original_created_at: datetime = entity.created_at

        # Act - simulate time passing
        entity.mark_as_updated()

        # Assert
        assert entity.created_at == original_created_at  # Should not change
        assert entity.updated_at > original_created_at  # Should change

    def test_get_identity_returns_entity_id(self) -> None:
        """Test get_identity returns the entity's ID."""
        # Arrange
        entity = TestEntity(name="test", id=123)

        # Act
        identity: int = entity.get_identity()

        # Assert
        assert identity == 123

    def test_entity_equality_based_on_identity(self) -> None:
        """Test that entities are equal if they have same ID (identity-based equality)."""
        # Arrange
        value_id = 1
        entity1 = TestEntity(name="different_name1", id=value_id, value=100)
        entity2 = TestEntity(
            name="different_name2", id=value_id, value=200
        )  # Same ID, different attributes

        # Act & Assert
        assert entity1 == entity2  # Should be equal because same ID

    def test_entity_inequality_different_identities(self) -> None:
        """Test that entities with different IDs are not equal."""
        # Arrange
        entity1 = TestEntity(name="same_name", id=1, value=100)
        entity2 = TestEntity(
            name="same_name", id=2, value=100
        )  # Same attributes, different ID

        # Act & Assert
        assert entity1 != entity2  # Should not be equal because different ID

    @pytest.mark.parametrize("entity_id", [1, 100, 999999, 2147483647])
    def test_entity_with_various_valid_ids(self, entity_id: int) -> None:
        """Test entity creation with various valid positive IDs."""
        # Act
        value_id = entity_id
        entity = TestEntity(name="test", id=value_id)

        # Assert
        assert entity.get_identity() == entity_id
        assert entity.id == value_id

    # Serialization tests inherited from BaseDomainObject are covered in base tests
    # Only testing entity-specific serialization aspects here

    def test_entity_serialization_includes_identity(self) -> None:
        """Test entity serialization includes identity fields."""
        # Arrange
        value_id = 123
        entity = TestEntity(name="test", id=value_id, value=456)

        # Act
        serialized: dict[str, Any] = entity.to_dict()

        # Assert
        assert serialized["id"] == 123
        assert serialized["name"] == "test"
        assert serialized["value"] == 456
        assert isinstance(serialized["created_at"], datetime)
        assert isinstance(serialized["updated_at"], datetime)
        assert serialized["is_active"] is True
        assert serialized["deleted_at"] is None

    def test_entity_deserialization_preserves_identity(self) -> None:
        """Test entity deserialization preserves identity."""
        # Arrange
        data: dict[str, Any] = {
            "id": 123,
            "name": "test",
            "value": 456,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        # Act
        entity: TestEntity = TestEntity.from_dict(data)

        # Assert
        assert isinstance(entity, TestEntity)
        assert entity.get_identity() == 123
        assert entity.id == 123

    def test_entity_identity_consistency_across_operations(self) -> None:
        """Test that entity identity remains consistent across operations."""
        # Arrange
        entity: TestEntity = TestEntity(name="test", id=123)
        original_identity: int = entity.get_identity()

        # Act - Perform various operations
        entity.mark_as_updated()
        entity.name = "updated_name"

        # Assert
        assert (
            entity.get_identity() == original_identity
        )  # Identity should never change

    def test_base_entity_configuration_validate_assignment(self) -> None:
        """Test that validate_assignment is enabled for entities."""
        # Arrange
        entity = TestEntity(name="test", id=1)

        # Act & Assert - Should validate when assigning new values
        entity.name = "new_name"  # Should work with valid data
        assert entity.name == "new_name"

        # Invalid assignment should raise validation error
        with pytest.raises(ValueError):
            entity.id = 0  # Invalid ID should be caught

    def test_base_entity_configuration_strips_whitespace(self) -> None:
        """Test that string fields strip whitespace automatically."""
        # Act
        entity = TestEntity(name="  test with spaces  ", id=1)

        # Assert
        assert entity.name == "test with spaces"  # Should be stripped

    def test_base_entity_mutable_unlike_value_objects(self) -> None:
        """Test that entities are mutable (unlike value objects)."""
        # Arrange
        entity = TestEntity(name="original", id=1, value=100)

        # Act - Should be able to modify entity fields
        entity.name = "modified"
        entity.value = 200
        entity.mark_as_updated()

        # Assert
        assert entity.name == "modified"
        assert entity.value == 200

    def test_is_new_entity_with_no_id(self) -> None:
        """Test is_new_entity returns True for entities without ID."""
        # Arrange
        entity = TestEntity(name="test")  # No ID provided

        # Act & Assert
        assert entity.is_new_entity() is True
        assert entity.is_persisted() is False

    def test_is_new_entity_with_none_id(self) -> None:
        """Test is_new_entity returns True for entities with None ID."""
        # Arrange
        entity = TestEntity(name="test", id=None)

        # Act & Assert
        assert entity.is_new_entity() is True
        assert entity.is_persisted() is False

    def test_is_persisted_with_valid_id(self) -> None:
        """Test is_persisted returns True for entities with valid positive ID."""
        # Arrange
        entity = TestEntity(name="test", id=123)

        # Act & Assert
        assert entity.is_persisted() is True
        assert entity.is_new_entity() is False

    def test_get_identity_with_valid_id(self) -> None:
        """Test get_identity returns ID for persisted entities."""
        # Arrange
        entity = TestEntity(name="test", id=123)

        # Act
        identity: int = entity.get_identity()

        # Assert
        assert identity == 123

    def test_get_identity_raises_error_for_new_entity(self) -> None:
        """Test get_identity raises error for new entities without ID."""
        # Arrange
        entity = TestEntity(name="test")  # New entity without ID

        # Act & Assert
        with pytest.raises(
            ValueError, match="Cannot get identity of a new entity without ID"
        ):
            entity.get_identity()

    def test_get_identity_raises_error_for_none_id(self) -> None:
        """Test get_identity raises error for entities with None ID."""
        # Arrange
        entity = TestEntity(name="test", id=None)

        # Act & Assert
        with pytest.raises(
            ValueError, match="Cannot get identity of a new entity without ID"
        ):
            entity.get_identity()
