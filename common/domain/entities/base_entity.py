from abc import ABC
from datetime import datetime

from pydantic import ConfigDict, Field

from common.domain import base_domain_object


class BaseEntity(base_domain_object.BaseDomainObject, ABC):
    """
    Base class for all Domain Entities.

    Entities have identity and their state can change over time.
    The identity is what makes them unique, not their attributes.
    """

    model_config: ConfigDict = {
        "validate_assignment": True,  # Validate when changing attributes
        "str_strip_whitespace": True,  # Strip whitespace from string fields
        "arbitrary_types_allowed": True,  # Entities can have complex types
        "use_enum_values": True,  # Use enum values directly in serialization
        "from_attributes": True,  # Allow instantiation from attributes
    }

    id: int | None = Field(
        default=None, gt=0, description="Unique identifier for the entity"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(default=True, description="Is the entity currently active")
    deleted_at: datetime | None = Field(
        default=None, description="Timestamp when the entity was deleted"
    )

    def mark_as_updated(self) -> None:
        """Mark the entity as updated with current timestamp."""
        self.updated_at = datetime.now()

    def is_new_entity(self) -> bool:
        """Check if this is a new entity (not yet persisted)."""
        return self.id is None

    def is_persisted(self) -> bool:
        """Check if this entity has been persisted to the database."""
        return self.id is not None

    def get_identity(self) -> int:
        """Get the unique identity of this entity."""
        if self.is_new_entity() or self.id is None:
            raise ValueError("Cannot get identity of a new entity without ID")
        return self.id

    def __eq__(self, other: object) -> bool:
        """
        Entities are equal if they have the same identity.
        This is different from Value Objects which compare all attributes.
        """
        if not isinstance(other, self.__class__):
            return False
        return self.get_identity() == other.get_identity()

    def __hash__(self) -> int:
        """Hash based on identity for use in sets/dicts."""
        return hash((self.__class__, self.get_identity()))
