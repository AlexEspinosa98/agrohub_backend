"""
API response DTOs for paginated responses.

What does this do?
- Wraps paginated data in standard API response format
- Combines pagination with success/error structure
- Provides factory methods for consistent responses
- Integrates with common ApiResponseDTO pattern
"""

from typing import Generic, TypeVar

from common.application.dtos import (
    output_dto as application_output_dtos,
    input_dto as application_input_dtos,
)
from common.infrastructure.api import dtos as common_infrastructure_dtos


TResponseData = TypeVar("TResponseData")


class PaginatedApiResponseDTO(
    common_infrastructure_dtos.ApiResponseDTO[
        application_output_dtos.PaginatedOutputDTO[TResponseData]
    ],
    Generic[TResponseData],
):
    """
    API response wrapper for paginated data.

    What does this do?
    - Combines standard API response structure with pagination
    - Provides consistent structure across all paginated endpoints
    - Includes success/error status and messages
    - Type-safe with generics
    """

    @classmethod
    def create_paginated_success(
        cls,
        items: list[TResponseData],
        pagination_input: application_input_dtos.PaginationInputDTO,
        total_items: int,
        message: str = "Data retrieved successfully",
    ) -> "PaginatedApiResponseDTO[TResponseData]":
        """
        Factory method to create successful paginated API response.

        What does this do?
        - Creates complete paginated response with metadata
        - Wraps in standard API response format
        - Generates success message automatically

        Args:
            items: List of items for current page
            pagination_input: Original pagination request
            total_items: Total count from database
            message: Success message

        Returns:
            Complete paginated API response
        """
        paginated_data: application_output_dtos.PaginatedOutputDTO = (
            application_output_dtos.PaginatedOutputDTO.create_response(
                items=items,
                pagination_input=pagination_input,
                total_items=total_items,
            )
        )

        return cls.success_response(
            data=paginated_data,
            message=message,
        )

    @classmethod
    def create_empty_response(
        cls,
        pagination_input: application_input_dtos.PaginationInputDTO,
        message: str = "No items found",
    ) -> "PaginatedApiResponseDTO[TResponseData]":
        """
        Factory method to create empty paginated response.

        What does this do?
        - Creates proper empty response with pagination metadata
        - Maintains consistent structure even when no data
        - Provides meaningful message for empty results

        Args:
            pagination_input: Original pagination request
            message: Message for empty response

        Returns:
            Empty paginated API response with proper structure
        """
        return cls.create_paginated_success(
            items=[],
            pagination_input=pagination_input,
            total_items=0,
            message=message,
        )

    class Config:
        json_schema_extra: dict[str, dict] = {
            "example": {
                "success": True,
                "message": "Data retrieved successfully",
                "data": {
                    "items": [],
                    "pagination": {
                        "current_page": 1,
                        "total_pages": 5,
                        "total_items": 50,
                        "has_next": True,
                        "has_previous": False,
                    },
                },
            }
        }
