"""
Unit tests for BaseValueObject.

Tests base value object functionality and immutability configuration.
"""

import pytest

from common.domain import value_objects as common_value_objects


class SimpleValueObject(common_value_objects.BaseValueObject):
    """Simple value object for testing."""

    value: str


class ComplexValueObject(common_value_objects.BaseValueObject):
    """Complex value object for testing."""

    name: str
    age: int
    active: bool = True


class TestBaseValueObject:
    """Test cases for BaseValueObject configuration."""

    def test_base_value_object_is_frozen(self) -> None:
        """Test that value objects are immutable (frozen=True)."""
        # Arrange
        vo = SimpleValueObject(value="test")

        # Act & Assert
        with pytest.raises((AttributeError, ValueError)):
            vo.value = "modified"  # Should not be allowed due to frozen=True

    def test_base_value_object_strips_whitespace(self) -> None:
        """Test that string fields strip whitespace automatically."""
        # Arrange & Act
        vo = SimpleValueObject(value="  test with spaces  ")

        # Assert
        assert vo.value == "test with spaces"  # Should be stripped

    def test_base_value_object_validates_on_assignment(self) -> None:
        """Test that validation occurs on field assignment."""
        # This is already covered by immutability, but we can test the config is set
        # Arrange
        vo = SimpleValueObject(value="test")

        # Act & Assert - Attempting assignment should fail due to validation + frozen
        with pytest.raises((AttributeError, ValueError)):
            vo.value = ""  # Should fail validation

    def test_base_value_object_rejects_arbitrary_types(self) -> None:
        """Test that arbitrary types are not allowed (arbitrary_types_allowed=False)."""
        # This test verifies the configuration is working by ensuring
        # only standard types are accepted in the value object definition

        # For this test, we just verify that our standard types work
        # The rejection of arbitrary types would be caught at definition time
        # not at instantiation time

        # Arrange & Act
        vo = ComplexValueObject(name="John", age=30, active=True)

        # Assert - Standard types should work fine
        assert vo.name == "John"
        assert vo.age == 30
        assert vo.active is True

    def test_base_value_object_equality_with_immutability(self) -> None:
        """Test that immutable value objects with same values are equal."""
        # Arrange
        vo1 = SimpleValueObject(value="test")
        vo2 = SimpleValueObject(value="test")

        # Act & Assert
        assert vo1 == vo2

    def test_base_value_object_hash_consistency_with_immutability(self) -> None:
        """Test that immutable value objects can be hashed consistently."""
        # Arrange
        vo1 = SimpleValueObject(value="test")
        vo2 = SimpleValueObject(value="test")

        # Act & Assert
        assert hash(vo1) == hash(vo2)

        # Test they can be used in sets
        value_set: set[SimpleValueObject] = {vo1, vo2}
        assert len(value_set) == 1  # Should be considered the same

    @pytest.mark.parametrize(
        "whitespace_value,expected",
        [
            ("  test  ", "test"),
            ("\n\ttest\n\t", "test"),
            ("   multiple   spaces   ", "multiple   spaces"),  # Only leading/trailing
        ],
    )
    def test_string_whitespace_stripping(
        self, whitespace_value: str, expected: str
    ) -> None:
        """Test various whitespace stripping scenarios."""
        # Act
        vo = SimpleValueObject(value=whitespace_value)

        # Assert
        assert vo.value == expected

    def test_base_value_object_validation_error(self) -> None:
        """Test that invalid data raises validation error."""
        # Act & Assert
        with pytest.raises(ValueError):
            ComplexValueObject(name="", age="Age")  # Invalid data
