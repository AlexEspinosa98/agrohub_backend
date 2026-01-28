import json
from typing import Any

import pytest

from common.domain import BaseDomainObject


class SimpleDomainObject(BaseDomainObject):
    """Simple domain object for testing."""

    value: str


class ComplexDomainObject(BaseDomainObject):
    """Complex domain object for testing."""

    name: str
    age: int
    active: bool = True


class TestBaseDomainObject:
    """Test cases for BaseDomainObject."""

    def test_base_domain_object_creation(self) -> None:
        """Test that domain object can be created with valid data."""
        # Act
        obj = SimpleDomainObject(value="test")

        # Assert
        assert obj.value == "test"

    def test_base_domain_object_equality_same_values(self) -> None:
        """Test that domain objects with same values are equal."""
        # Arrange
        obj1 = SimpleDomainObject(value="test")
        obj2 = SimpleDomainObject(value="test")

        # Act & Assert
        assert obj1 == obj2

    def test_base_domain_object_equality_different_values(self) -> None:
        """Test that domain objects with different values are not equal."""
        # Arrange
        obj1 = SimpleDomainObject(value="test1")
        obj2 = SimpleDomainObject(value="test2")

        # Act & Assert
        assert obj1 != obj2

    def test_base_domain_object_equality_different_types(self) -> None:
        """Test that domain objects of different types are not equal."""
        # Arrange
        simple_obj = SimpleDomainObject(value="test")
        complex_obj = ComplexDomainObject(name="test", age=25)

        # Act & Assert
        assert simple_obj != complex_obj

    def test_to_dict_simple_object(self) -> None:
        """Test converting simple domain object to dictionary."""
        # Arrange
        obj = SimpleDomainObject(value="test")

        # Act
        result: dict[str, Any] = obj.to_dict()

        # Assert
        assert isinstance(result, dict)
        assert result == {"value": "test"}

    def test_to_dict_complex_object(self) -> None:
        """Test converting complex domain object to dictionary."""
        # Arrange
        obj = ComplexDomainObject(name="John", age=30, active=False)

        # Act
        result: dict[str, Any] = obj.to_dict()

        # Assert
        assert isinstance(result, dict)
        assert result == {"name": "John", "age": 30, "active": False}

    def test_to_dict_with_defaults(self) -> None:
        """Test to_dict with default values."""
        # Arrange
        obj = ComplexDomainObject(name="Jane", age=25)  # active defaults to True

        # Act
        result: dict[str, Any] = obj.to_dict()

        # Assert
        assert result == {"name": "Jane", "age": 25, "active": True}

    def test_to_json_simple_object(self) -> None:
        """Test converting simple domain object to JSON string."""
        # Arrange
        obj = SimpleDomainObject(value="test")

        # Act
        result: str = obj.to_json()

        # Assert
        assert isinstance(result, str)
        parsed: dict[str, Any] = json.loads(result)
        assert parsed == {"value": "test"}

    def test_to_json_complex_object(self) -> None:
        """Test converting complex domain object to JSON string."""
        # Arrange
        obj = ComplexDomainObject(name="John", age=30, active=False)

        # Act
        result: str = obj.to_json()

        # Assert
        assert isinstance(result, str)
        parsed: dict[str, Any] = json.loads(result)
        assert parsed == {"name": "John", "age": 30, "active": False}

    def test_from_dict_simple_object(self) -> None:
        """Test creating simple domain object from dictionary."""
        # Arrange
        data: dict[str, str] = {"value": "test"}

        # Act
        obj: SimpleDomainObject = SimpleDomainObject.from_dict(data)

        # Assert
        assert isinstance(obj, SimpleDomainObject)
        assert type(obj) is SimpleDomainObject
        assert obj.value == "test"

    def test_from_dict_complex_object(self) -> None:
        """Test creating complex domain object from dictionary."""
        # Arrange
        data: dict[str, Any] = {"name": "John", "age": 30, "active": False}

        # Act
        obj: ComplexDomainObject = ComplexDomainObject.from_dict(data)

        # Assert
        assert isinstance(obj, ComplexDomainObject)
        assert type(obj) is ComplexDomainObject
        assert obj.name == "John"
        assert obj.age == 30
        assert obj.active is False

    def test_from_dict_with_defaults(self) -> None:
        """Test from_dict with default values."""
        # Arrange
        data: dict[str, Any] = {"name": "Jane", "age": 25}  # active not specified

        # Act
        obj: ComplexDomainObject = ComplexDomainObject.from_dict(data)

        # Assert
        assert obj.name == "Jane"
        assert obj.age == 25
        assert obj.active is True  # Default value

    def test_from_dict_with_invalid_data(self) -> None:
        """Test from_dict with invalid data raises error."""
        # Arrange
        invalid_data: dict[str, Any] = {"name": "John"}  # Missing required 'age' field

        # Act & Assert
        with pytest.raises(ValueError):
            ComplexDomainObject.from_dict(invalid_data)

    def test_from_json_simple_object(self) -> None:
        """Test creating simple domain object from JSON string."""
        # Arrange
        json_str = '{"value": "test"}'

        # Act
        obj: SimpleDomainObject = SimpleDomainObject.from_json(json_str)

        # Assert
        assert isinstance(obj, SimpleDomainObject)
        assert type(obj) is SimpleDomainObject
        assert obj.value == "test"

    def test_from_json_complex_object(self) -> None:
        """Test creating complex domain object from JSON string."""
        # Arrange
        json_str = '{"name": "John", "age": 30, "active": false}'

        # Act
        obj: ComplexDomainObject = ComplexDomainObject.from_json(json_str)

        # Assert
        assert isinstance(obj, ComplexDomainObject)
        assert type(obj) is ComplexDomainObject
        assert obj.name == "John"
        assert obj.age == 30
        assert obj.active is False

    def test_from_json_with_defaults(self) -> None:
        """Test from_json with default values."""
        # Arrange
        json_str = '{"name": "Jane", "age": 25}'  # active not specified

        # Act
        obj: ComplexDomainObject = ComplexDomainObject.from_json(json_str)

        # Assert
        assert obj.name == "Jane"
        assert obj.age == 25
        assert obj.active is True  # Default value

    def test_from_json_with_invalid_json(self) -> None:
        """Test from_json with invalid JSON raises error."""
        # Arrange
        invalid_json = '{"name": "John", "age": invalid}'

        # Act & Assert
        with pytest.raises(ValueError):
            ComplexDomainObject.from_json(invalid_json)

    def test_from_json_with_missing_required_field(self) -> None:
        """Test from_json with missing required field raises error."""
        # Arrange
        json_str = '{"name": "John"}'  # Missing required 'age' field

        # Act & Assert
        with pytest.raises(ValueError):
            ComplexDomainObject.from_json(json_str)

    def test_round_trip_serialization_dict(self) -> None:
        """Test round-trip serialization: object -> dict -> object."""
        # Arrange
        original = ComplexDomainObject(name="John", age=30, active=False)

        # Act
        dict_data: dict[str, Any] = original.to_dict()
        restored: ComplexDomainObject = ComplexDomainObject.from_dict(dict_data)

        # Assert
        assert original == restored
        assert original.name == restored.name
        assert original.age == restored.age
        assert original.active == restored.active

    def test_round_trip_serialization_json(self) -> None:
        """Test round-trip serialization: object -> JSON -> object."""
        # Arrange
        original = ComplexDomainObject(name="John", age=30, active=False)

        # Act
        json_str: str = original.to_json()
        restored: ComplexDomainObject = ComplexDomainObject.from_json(json_str)

        # Assert
        assert original == restored
        assert original.name == restored.name
        assert original.age == restored.age
        assert original.active == restored.active

    @pytest.mark.parametrize("value", ["test1", "test2", "another_value"])
    def test_serialization_with_various_values(self, value: str) -> None:
        """Test serialization with various values."""
        # Arrange
        obj = SimpleDomainObject(value=value)

        # Act
        dict_result: dict[str, Any] = obj.to_dict()
        json_result: str = obj.to_json()

        # Assert
        assert dict_result["value"] == value
        assert value in json_result

    def test_base_domain_object_serialization(self) -> None:
        """Test that domain object can be serialized."""
        # Arrange
        obj = ComplexDomainObject(name="John", age=30, active=False)

        # Act
        serialized: dict[str, Any] = obj.model_dump()

        # Assert
        assert isinstance(serialized, dict)
        assert serialized["name"] == "John"
        assert serialized["age"] == 30
        assert serialized["active"] is False
