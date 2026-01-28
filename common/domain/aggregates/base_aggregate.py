from abc import ABC, abstractmethod
from typing import Any

from pydantic import ConfigDict

from common.domain.base_domain_object import BaseDomainObject


class BaseAggregate(BaseDomainObject, ABC):
    """
    Base class for all Domain Aggregates.

    Aggregates are consistency boundaries that group related entities and value objects.
    They ensure business rules are enforced and handle domain events.
    """

    model_config: ConfigDict = {
        "validate_assignment": True,  # Validate when changing attributes
        "str_strip_whitespace": True,  # Automatically strip whitespace from strings
        "arbitrary_types_allowed": True,  # Allow complex types like entities and value objects
        "use_enum_values": True,  # Use enum values directly in serialization
    }

    @abstractmethod
    def get_aggregate_id(self) -> Any:
        """
        Get the unique identifier for this aggregate.
        Each aggregate must define what identifies it.
        """

    @abstractmethod
    def validate_invariants(self) -> None:
        """
        Validate business invariants for this aggregate.
        Should raise domain exceptions if invariants are violated.
        """
