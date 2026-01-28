"""
Base Domain Object for all domain objects.

Provides common functionality for serialization and conversion
following DDD principles.
"""

from typing import Any, TypeVar

from pydantic import BaseModel


TDomainObject = TypeVar("TDomainObject", bound="BaseDomainObject")


class BaseDomainObject(BaseModel):
    """
    Base class for all domain objects (Entities, Value Objects, Aggregates).

    Provides common functionality for:
    - Serialization/Deserialization
    - Dictionary conversion
    - JSON conversion
    - Validation
    """

    def to_dict(self) -> dict[str, Any]:
        """
        Convert domain object to dictionary.

        Returns:
            dict[str, Any]: Dictionary representation
        """
        return self.model_dump()

    def to_json(self) -> str:
        """
        Convert domain object to JSON string.

        Returns:
            str: JSON representation
        """
        return self.model_dump_json()

    @classmethod
    def from_dict(cls: type[TDomainObject], data: dict[str, Any]) -> TDomainObject:
        """
        Create domain object from dictionary.

        Args:
            data (dict[str, Any]): Dictionary containing object data

        Returns:
            TDomainObject: New domain object instance of the calling class type
        """
        return cls.model_validate(data)

    @classmethod
    def from_json(cls: type[TDomainObject], json_str: str) -> TDomainObject:
        """
        Create domain object from JSON string.

        Args:
            json_str (str): JSON string containing object data

        Returns:
            TDomainObject: New domain object instance of the calling class type
        """
        return cls.model_validate_json(json_str)
