"""
Unit tests for BaseAggregate.

Tests base aggregate functionality specific to aggregates.
"""

from typing import Any

import pytest

from common.domain import (
    aggregates as common_aggregates,
    entities as common_entities,
    enums as common_enums,
    value_objects as common_value_objects,
)


class TestChildEntity(common_entities.BaseEntity):
    """Test child entity for aggregate testing."""

    name: str
    aggregate_id: int


class TestValueObject(common_value_objects.BaseValueObject):
    """Test value object for aggregate testing."""

    value: str


class TestAggregate(common_aggregates.BaseAggregate):
    """Test aggregate for base aggregate testing."""

    aggregate_id: int
    name: str
    children: list[TestChildEntity] = []
    test_vo: TestValueObject | None = None
    status: common_enums.UserStatus = common_enums.UserStatus.ACTIVE

    def get_aggregate_id(self) -> int:
        """Get the aggregate root ID."""
        return self.aggregate_id

    def validate_invariants(self) -> None:
        """Validate aggregate business rules."""
        if len(self.children) > 5:
            raise ValueError("Aggregate cannot have more than 5 children")
        if not self.name.strip():
            raise ValueError("Aggregate name cannot be empty")

    def add_child(self, child: TestChildEntity) -> None:
        """Add child entity to aggregate."""
        self.children.append(child)


class TestBaseAggregate:
    """Test cases for BaseAggregate."""

    def test_base_aggregate_cannot_be_instantiated_directly(self) -> None:
        """Test that BaseAggregate is abstract and cannot be instantiated."""
        # Act & Assert
        with pytest.raises(TypeError):
            common_aggregates.BaseAggregate()

    def test_base_aggregate_creation_with_concrete_implementation(self) -> None:
        """Test that concrete aggregate can be created."""
        # Act
        aggregate = TestAggregate(aggregate_id=1, name="test")

        # Assert
        assert aggregate.aggregate_id == 1
        assert aggregate.name == "test"
        assert aggregate.get_aggregate_id() == 1

    def test_base_aggregate_configuration_validate_assignment(self) -> None:
        """Test that validate_assignment is enabled for aggregates."""
        # Arrange
        aggregate = TestAggregate(aggregate_id=1, name="test")

        # Act & Assert - Should validate when assigning new values
        aggregate.name = "new_name"  # Should work with valid data
        assert aggregate.name == "new_name"

        # Invalid assignment should raise validation error if validation exists
        aggregate.status = (
            common_enums.UserStatus.CREATED
        )  # Should work with valid enum

        assert aggregate.status == common_enums.UserStatus.CREATED.value

    def test_base_aggregate_configuration_strips_whitespace(self) -> None:
        """Test that string fields strip whitespace automatically."""
        # Act
        aggregate = TestAggregate(aggregate_id=1, name="  test with spaces  ")

        # Assert
        assert aggregate.name == "test with spaces"  # Should be stripped

    def test_base_aggregate_configuration_allows_arbitrary_types(self) -> None:
        """Test that aggregates can have complex types (arbitrary_types_allowed=True)."""
        # Arrange
        child_entity = TestChildEntity(id=1, name="child", aggregate_id=1)
        value_object = TestValueObject(value="test")

        # Act
        aggregate = TestAggregate(aggregate_id=1, name="test")
        aggregate.add_child(child_entity)
        aggregate.test_vo = value_object  # Add value object

        # Assert - Complex types should work
        assert isinstance(aggregate.children[0], TestChildEntity)
        assert isinstance(aggregate.test_vo, TestValueObject)

    def test_base_aggregate_configuration_enum_values_serialization(self) -> None:
        """Test that enums are serialized as values (use_enum_values=True)."""
        # Arrange
        aggregate = TestAggregate(aggregate_id=1, name="test")
        aggregate.status = common_enums.UserStatus.ACTIVE

        # Act
        serialized: dict[str, Any] = aggregate.to_dict()

        # Assert - Should serialize enum as value, not as enum object
        assert isinstance(serialized, dict)
        assert "status" in serialized
        # The enum should be serialized as its value
        assert isinstance(serialized["status"], str)

    def test_get_aggregate_id_abstract_method_implementation(self) -> None:
        """Test that get_aggregate_id abstract method must be implemented."""
        # Arrange
        aggregate = TestAggregate(aggregate_id=123, name="test")

        # Act
        result: int = aggregate.get_aggregate_id()

        # Assert
        assert result == 123

    def test_validate_invariants_abstract_method_implementation(self) -> None:
        """Test that validate_invariants abstract method must be implemented."""
        # Arrange
        aggregate = TestAggregate(aggregate_id=1, name="test")

        # Act & Assert - Should not raise exception with valid state
        aggregate.validate_invariants()  # Should pass

    def test_validate_invariants_with_business_rule_violation(self) -> None:
        """Test that validate_invariants raises exception when business rules are violated."""
        # Arrange
        aggregate = TestAggregate(aggregate_id=1, name="test")

        # Add too many children to violate business rule
        for i in range(6):  # More than allowed limit of 5
            child = TestChildEntity(
                id=i + 1,
                name=f"child_{i}",
                aggregate_id=1,
            )
            aggregate.add_child(child)

        # Act & Assert
        with pytest.raises(ValueError, match="cannot have more than 5 children"):
            aggregate.validate_invariants()

    def test_validate_invariants_with_empty_name_violation(self) -> None:
        """Test that validate_invariants raises exception for empty name."""
        # Arrange
        aggregate = TestAggregate(aggregate_id=1, name="   ")  # Whitespace only

        # Act & Assert
        with pytest.raises(ValueError, match="name cannot be empty"):
            aggregate.validate_invariants()

    def test_base_aggregate_mutable_unlike_value_objects(self) -> None:
        """Test that aggregates are mutable (unlike value objects)."""
        # Arrange
        aggregate = TestAggregate(aggregate_id=1, name="original")

        # Act - Should be able to modify aggregate
        aggregate.name = "modified"
        child = TestChildEntity(id=1, name="child", aggregate_id=1)
        aggregate.add_child(child)

        # Assert
        assert aggregate.name == "modified"
        assert len(aggregate.children) == 1

    def test_base_aggregate_domain_specific_behavior(self) -> None:
        """Test BaseAggregate behavior in domain-specific contexts."""
        # Arrange
        aggregate = TestAggregate(aggregate_id=123, name="test")

        # Act & Assert - Domain rules
        assert aggregate.get_aggregate_id() == 123
        assert isinstance(aggregate.get_aggregate_id(), int)

        # Aggregate can contain multiple domain objects
        child = TestChildEntity(id=1, name="child", aggregate_id=123)
        aggregate.add_child(child)
        assert len(aggregate.children) == 1

    def test_base_aggregate_serialization_includes_aggregate_fields(self) -> None:
        """Test aggregate serialization includes aggregate-specific fields."""
        # Arrange
        aggregate = TestAggregate(aggregate_id=123, name="test")
        aggregate.status = common_enums.UserStatus.ACTIVE

        # Act
        serialized: dict[str, Any] = aggregate.to_dict()

        # Assert
        assert "aggregate_id" in serialized
        assert "name" in serialized
        assert "status" in serialized
        assert serialized["aggregate_id"] == 123
        assert serialized["name"] == "test"

    def test_base_aggregate_deserialization_with_complex_types(self) -> None:
        """Test aggregate deserialization with complex types."""
        # Arrange
        data: dict[str, Any] = {
            "aggregate_id": 456,
            "name": "deserialized",
            "status": common_enums.UserStatus.ACTIVE.value,
        }

        # Act
        aggregate: TestAggregate = TestAggregate.from_dict(data)

        # Assert
        assert isinstance(aggregate, TestAggregate)
        assert aggregate.get_aggregate_id() == 456
        assert aggregate.name == "deserialized"

    @pytest.mark.parametrize("children_count", [0, 1, 3, 5])
    def test_validate_invariants_with_valid_children_counts(
        self, children_count: int
    ) -> None:
        """Test validate_invariants with various valid children counts."""
        # Arrange
        aggregate = TestAggregate(aggregate_id=1, name="test")

        for i in range(children_count):
            child = TestChildEntity(
                id=i + 1,
                name=f"child_{i}",
                aggregate_id=1,
            )
            aggregate.add_child(child)

        # Act & Assert - Should not raise exception
        aggregate.validate_invariants()
        assert len(aggregate.children) == children_count

    def test_base_aggregate_identity_consistency(self) -> None:
        """Test that aggregate identity remains consistent."""
        # Arrange
        aggregate = TestAggregate(aggregate_id=123, name="test")
        original_id: int = aggregate.get_aggregate_id()

        # Act - Perform various operations
        aggregate.name = "modified"
        child = TestChildEntity(id=1, name="child", aggregate_id=123)
        aggregate.add_child(child)

        # Assert
        assert (
            aggregate.get_aggregate_id() == original_id
        )  # Identity should never change
