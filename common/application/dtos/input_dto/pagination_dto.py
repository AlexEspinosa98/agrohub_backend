from typing import TypeVar

from pydantic import Field

from common.application import dtos as common_dtos
from common.domain import enums as common_enums


TDataItem = TypeVar("TDataItem")


class PaginationInputDTO(common_dtos.BaseDTO):
    """
    DTO for receiving pagination parameters.

    What does it do?
    - Validates that page >= 1 and limit between 1-100
    - Calculates offset for database queries
    - Standardizes how we receive pagination throughout the app
    """

    page: int = Field(default=1, ge=1, description="Page number (1-based indexing)")
    limit: int = Field(
        default=10, ge=1, le=100, description="Items per page (maximum 100)"
    )
    sort_by: str | None = Field(default="created_at", description="Field to sort by")
    sort_direction: common_enums.SortDirection | None = Field(
        default=common_enums.SortDirection.DESC, description="Sort direction (asc/desc)"
    )

    @property
    def offset(self) -> int:
        """
        Property to get offset for database queries.

        What does it do?
        - Uses the calculate_offset method to get the offset
        - Makes it easy to access without calling a method
        """
        return self.calculate_offset()

    def calculate_offset(self) -> int:
        """
        Calculate offset for database queries.

        What does it do?
        - Converts page (1-based) to offset (0-based)
        - Example: page 2, limit 10 → offset 10
        """
        return (self.page - 1) * self.limit

    def as_pagination_spec(self) -> "PaginationInputDTO":
        """
        Extract pagination spec from composite DTO.

        What does it do?
        - Returns a pure PaginationInputDTO with only pagination fields
        - Useful when you need to pass pagination to infrastructure layers
        - Implements interface segregation principle
        """
        return PaginationInputDTO(
            page=self.page,
            limit=self.limit,
            sort_by=self.sort_by,
            sort_direction=self.sort_direction,
        )
