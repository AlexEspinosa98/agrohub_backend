from typing import Generic, TypeVar

from pydantic import Field

from common.application import dtos as common_dtos
from common.application.dtos import input_dto as common_input_dtos


TDataItem = TypeVar("TDataItem")


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


class PaginatedOutputDTO(common_dtos.BaseDTO, Generic[TDataItem]):
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
        pagination_input: common_input_dtos.PaginationInputDTO,
        total_items: int,
    ) -> "PaginatedOutputDTO[TDataItem]":
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

    @property
    def total_items(self) -> int:
        """Get total items from pagination metadata."""
        return self.pagination.total_items
