"""
Unit tests for pagination API response DTOs.
"""

from pydantic import BaseModel

from common.application.dtos import (
    input_dto as common_input_dto,
    output_dto as common_output_dto,
)
from common.infrastructure.api.dtos import pagination_response_dto


class TestPaginatedApiResponseDTO:
    """Tests for PaginatedApiResponseDTO."""

    def test_create_paginated_success(self) -> None:
        """Test creating successful paginated API response."""
        # Arrange
        items: list[str] = ["item1", "item2", "item3"]
        pagination_input = common_input_dto.PaginationInputDTO(page=1, limit=10)
        total_items = 25
        message = "Successfully retrieved data"

        # Act
        response: pagination_response_dto.PaginatedApiResponseDTO = (
            pagination_response_dto.PaginatedApiResponseDTO.create_paginated_success(
                items=items,
                pagination_input=pagination_input,
                total_items=total_items,
                message=message,
            )
        )

        # Assert
        assert response.success is True
        assert response.message == message
        assert response.data.items == items
        assert response.data.pagination.total_items == total_items
        assert response.data.pagination.current_page == 1

    def test_create_empty_response(self) -> None:
        """Test creating empty paginated response."""
        # Arrange
        pagination_input = common_input_dto.PaginationInputDTO(page=1, limit=10)
        message = "No data found"

        # Act
        response: pagination_response_dto.PaginatedApiResponseDTO = (
            pagination_response_dto.PaginatedApiResponseDTO.create_empty_response(
                pagination_input=pagination_input,
                message=message,
            )
        )

        # Assert
        assert response.success is True
        assert response.message == message
        assert response.data.items == []
        assert response.data.pagination.total_items == 0

    def test_pagination_metadata_consistency(self) -> None:
        """Test that pagination metadata is consistent across the response."""
        # Arrange
        items: list[str] = ["a", "b", "c", "d", "e"]
        pagination_input = common_input_dto.PaginationInputDTO(page=2, limit=3)
        total_items = 15

        # Act
        response: pagination_response_dto.PaginatedApiResponseDTO = (
            pagination_response_dto.PaginatedApiResponseDTO.create_paginated_success(
                items=items,
                pagination_input=pagination_input,
                total_items=total_items,
            )
        )

        # Assert
        pagination: common_output_dto.PaginationMetadataDTO = response.data.pagination
        assert pagination.current_page == 2
        assert pagination.total_items == 15
        assert pagination.total_pages == 5
        assert pagination.has_previous is True
        assert pagination.has_next is True

    def test_type_safety_with_generic(self) -> None:
        """Test type safety with generic types."""

        # Arrange
        class TestItem(BaseModel):
            value: str

        items: list[TestItem] = [TestItem(value="test1"), TestItem(value="test2")]
        pagination_input = common_input_dto.PaginationInputDTO(page=1, limit=10)

        # Act
        response: pagination_response_dto.PaginatedApiResponseDTO[TestItem] = (
            pagination_response_dto.PaginatedApiResponseDTO.create_paginated_success(
                items=items,
                pagination_input=pagination_input,
                total_items=2,
            )
        )

        # Assert
        assert len(response.data.items) == 2
        assert response.data.items[0].value == "test1"
        assert response.data.items[1].value == "test2"

    def test_default_messages(self) -> None:
        """Test default messages are applied correctly."""
        # Arrange
        pagination_input = common_input_dto.PaginationInputDTO(page=1, limit=10)

        # Act - Success with default message
        success_response: pagination_response_dto.PaginatedApiResponseDTO = (
            pagination_response_dto.PaginatedApiResponseDTO.create_paginated_success(
                items=["item"],
                pagination_input=pagination_input,
                total_items=1,
            )
        )

        # Act - Empty with default message
        empty_response: pagination_response_dto.PaginatedApiResponseDTO = (
            pagination_response_dto.PaginatedApiResponseDTO.create_empty_response(
                pagination_input=pagination_input,
            )
        )

        # Assert
        assert success_response.message == "Data retrieved successfully"
        assert empty_response.message == "No items found"
