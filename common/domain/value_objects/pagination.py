from typing import Generic, TypeVar

from common.domain import value_objects as common_value_objects


EntityType = TypeVar("EntityType")


class PaginatedResult(common_value_objects.BaseValueObject, Generic[EntityType]):
    """
    Generic value object for paginated domain results.

    This is a pure domain concept - represents a "page" of domain entities
    with total count information. Can be used by any repository.
    """

    items: list[EntityType]
    total_count: int
