"""
Common pagination DTOs for application layer.

These DTOs define the contract for:
1. Receiving pagination parameters (page, limit)
2. Returning pagination metadata (totals, navigation)
3. Structuring paginated responses
"""

from typing import Generic, TypeVar

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


class PaginationMetadataDTO(common_dtos.BaseDTO):
    """
    DTO with essential pagination metadata.

    What does it do?
    - Provides basic info to frontend for navigation
    - Only the necessary: current page, total pages, total items, navigation
    """

    current_page: int = Field(description="Current page number")
    total_pages: int = Field(description="Total number of pages")
    total_items: int = Field(description="Total number of items")
    has_next: bool = Field(description="Whether there is a next page")
    has_previous: bool = Field(description="Whether there is a previous page")

    @classmethod
    def create_from_pagination(
        cls,
        current_page: int,
        items_per_page: int,
        total_items: int,
    ) -> "PaginationMetadataDTO":
        """
        Factory method to create metadata from basic parameters.

        What does it do?
        - Automatically calculates total_pages, has_next, has_previous
        - Avoids repeating this logic in each use case
        """
        # Total pages: at least 1, even if no items
        total_pages: int = (
            max(1, (total_items + items_per_page - 1) // items_per_page)
            if total_items > 0
            else 1
        )

        # Navigation
        has_previous: bool = current_page > 1
        has_next: bool = current_page < total_pages

        return cls(
            current_page=current_page,
            total_pages=total_pages,
            total_items=total_items,
            has_next=has_next,
            has_previous=has_previous,
        )


class PaginatedResponseDTO(common_dtos.BaseDTO, Generic[TDataItem]):
    """
    Generic DTO for paginated responses.

    What does it do?
    - Combines items + pagination metadata
    - Is reusable for any type of item (Generic)
    - Standardizes all paginated responses
    """

    items: list[TDataItem] = Field(description="List of items for current page")
    pagination: PaginationMetadataDTO = Field(description="Pagination metadata")

    @classmethod
    def create_response(
        cls,
        items: list[TDataItem],
        pagination_input: PaginationInputDTO,
        total_items: int,
    ) -> "PaginatedResponseDTO[TDataItem]":
        """
        Factory method to create paginated response.

        What does it do?
        - Makes it easy to create from use cases
        - Automatically generates metadata
        """
        pagination_metadata: PaginationMetadataDTO = (
            PaginationMetadataDTO.create_from_pagination(
                current_page=pagination_input.page,
                items_per_page=pagination_input.limit,
                total_items=total_items,
            )
        )

        return cls(
            items=items,
            pagination=pagination_metadata,
        )

    def is_empty(self) -> bool:
        """Check if response is empty."""
        return len(self.items) == 0

    @property
    def total_items(self) -> int:
        """Get total items from pagination metadata."""
        return self.pagination.total_items
