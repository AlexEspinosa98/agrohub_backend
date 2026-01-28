from pydantic import ConfigDict

from common.domain.base_domain_object import BaseDomainObject


class BaseValueObject(BaseDomainObject):
    """
    Base class for all Value Objects in the domain.

    Provides common functionality for immutability, serialization,
    and comparison following DDD principles.
    """

    model_config: ConfigDict = {
        "frozen": True,  # Immutability
        "str_strip_whitespace": True,  # Clean strings automatically
        "validate_assignment": True,  # Validate on field assignment
        "arbitrary_types_allowed": True,  # Allow arbitrary types
    }
