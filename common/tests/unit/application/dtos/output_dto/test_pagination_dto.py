"""
Unit tests for pagination DTOs.

Tests validation, factory methods, and edge cases for pagination components.
"""

from common.application.dtos import (
    input_dto as common_input_dto,
    output_dto as common_output_dto,
)


class TestPaginationMetadataDTO:
    """Tests for PaginationMetadataDTO factory method and calculations."""

    def test_create_from_pagination_basic_case(self) -> None:
        """Test metadata creation for a typical pagination scenario."""
        # Act
        metadata: common_output_dto.PaginationMetadataDTO = (
            common_output_dto.PaginationMetadataDTO.create_from_pagination(
                current_page=2,
                items_per_page=10,
                total_items=35,
            )
        )

        # Assert
        assert metadata.current_page == 2
        assert metadata.total_pages == 4
        assert metadata.total_items == 35
        assert metadata.has_next is True
        assert metadata.has_previous is True

    def test_create_from_pagination_first_page(self) -> None:
        """Test metadata for first page navigation."""
        # Act
        metadata: common_output_dto.PaginationMetadataDTO = (
            common_output_dto.PaginationMetadataDTO.create_from_pagination(
                current_page=1,
                items_per_page=10,
                total_items=25,
            )
        )

        # Assert
        assert metadata.current_page == 1
        assert metadata.has_previous is False
        assert metadata.has_next is True

    def test_create_from_pagination_last_page(self) -> None:
        """Test metadata for last page navigation."""
        # Act
        metadata: common_output_dto.PaginationMetadataDTO = (
            common_output_dto.PaginationMetadataDTO.create_from_pagination(
                current_page=3,
                items_per_page=10,
                total_items=25,
            )
        )

        # Assert
        assert metadata.current_page == 3
        assert metadata.total_pages == 3
        assert metadata.has_previous is True
        assert metadata.has_next is False

    def test_create_from_pagination_empty_dataset(self) -> None:
        """Test metadata creation when no items exist."""
        # Act
        metadata: common_output_dto.PaginationMetadataDTO = (
            common_output_dto.PaginationMetadataDTO.create_from_pagination(
                current_page=1,
                items_per_page=10,
                total_items=0,
            )
        )

        # Assert
        assert metadata.current_page == 1
        assert metadata.total_pages == 1
        assert metadata.total_items == 0
        assert metadata.has_next is False
        assert metadata.has_previous is False

    def test_create_from_pagination_single_page_with_items(self) -> None:
        """Test metadata when all items fit on one page."""
        # Act
        metadata: common_output_dto.PaginationMetadataDTO = (
            common_output_dto.PaginationMetadataDTO.create_from_pagination(
                current_page=1,
                items_per_page=20,
                total_items=15,
            )
        )

        # Assert
        assert metadata.current_page == 1
        assert metadata.total_pages == 1
        assert metadata.total_items == 15
        assert metadata.has_next is False
        assert metadata.has_previous is False


class TestPaginatedOutputDTO:
    """Tests for PaginatedOutputDTO creation and utility methods."""

    def test_create_response_with_items(self) -> None:
        """Test creating paginated response with items."""
        # Arrange
        items: list[str] = ["item1", "item2", "item3"]
        pagination_input = common_input_dto.PaginationInputDTO(page=1, limit=10)
        total_items = 25

        # Act
        response: common_output_dto.PaginatedOutputDTO = (
            common_output_dto.PaginatedOutputDTO.create_response(
                items=items,
                pagination_input=pagination_input,
                total_items=total_items,
            )
        )

        # Assert
        assert response.items == items
        assert response.pagination.current_page == 1
        assert response.pagination.total_items == 25
        assert response.pagination.total_pages == 3
        assert response.total_items == 25

    def test_create_response_empty(self) -> None:
        """Test creating empty paginated response."""
        # Arrange
        items: list[str] = []
        pagination_input = common_input_dto.PaginationInputDTO(page=1, limit=10)
        total_items = 0

        # Act
        response: common_output_dto.PaginatedOutputDTO = (
            common_output_dto.PaginatedOutputDTO.create_response(
                items=items,
                pagination_input=pagination_input,
                total_items=total_items,
            )
        )

        # Assert
        assert response.items == []
        assert response.pagination.total_items == 0
        assert response.total_items == 0


class TestPaginationEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_exactly_divisible_items(self) -> None:
        """Test when total items divides evenly by page size."""
        # Act
        metadata: common_output_dto.PaginationMetadataDTO = (
            common_output_dto.PaginationMetadataDTO.create_from_pagination(
                current_page=2,
                items_per_page=10,
                total_items=20,  # Exactly 2 pages
            )
        )

        # Assert
        assert metadata.total_pages == 2
        assert metadata.current_page == 2
        assert metadata.has_next is False

    def test_one_item_over_page_boundary(self) -> None:
        """Test when total items is one more than page size."""
        # Act
        metadata: common_output_dto.PaginationMetadataDTO = (
            common_output_dto.PaginationMetadataDTO.create_from_pagination(
                current_page=1,
                items_per_page=10,
                total_items=11,  # Creates 2 pages
            )
        )

        # Assert
        assert metadata.total_pages == 2
        assert metadata.has_next is True

    def test_single_item_single_page(self) -> None:
        """Test pagination with only one item."""
        # Act
        metadata: common_output_dto.PaginationMetadataDTO = (
            common_output_dto.PaginationMetadataDTO.create_from_pagination(
                current_page=1,
                items_per_page=10,
                total_items=1,
            )
        )

        # Assert
        assert metadata.total_pages == 1
        assert metadata.has_next is False
        assert metadata.has_previous is False

    def test_very_large_page_size(self) -> None:
        """Test with page size larger than total items."""
        # Act
        metadata: common_output_dto.PaginationMetadataDTO = (
            common_output_dto.PaginationMetadataDTO.create_from_pagination(
                current_page=1,
                items_per_page=100,
                total_items=5,
            )
        )

        # Assert
        assert metadata.total_pages == 1
        assert metadata.has_next is False

    def test_minimum_valid_values(self) -> None:
        """Test with minimum valid pagination values."""
        # Act
        pagination = common_input_dto.PaginationInputDTO(page=1, limit=1)

        response: common_output_dto.PaginatedOutputDTO = (
            common_output_dto.PaginatedOutputDTO.create_response(
                items=["single_item"],
                pagination_input=pagination,
                total_items=5,
            )
        )

        # Assert
        assert response.pagination.current_page == 1
        assert response.pagination.total_pages == 5
        assert len(response.items) == 1

    def test_maximum_valid_limit(self) -> None:
        """Test with maximum allowed limit."""
        # Act
        pagination = common_input_dto.PaginationInputDTO(page=1, limit=100)

        # Assert
        assert pagination.limit == 100
        assert pagination.calculate_offset() == 0

    def test_page_beyond_total_pages(self) -> None:
        """Test metadata when requesting page beyond available pages."""
        # Act
        metadata: common_output_dto.PaginationMetadataDTO = (
            common_output_dto.PaginationMetadataDTO.create_from_pagination(
                current_page=10,  # Way beyond available pages
                items_per_page=10,
                total_items=25,  # Only 3 pages available
            )
        )

        # Assert
        assert metadata.current_page == 10
        assert metadata.total_pages == 3
        assert metadata.has_next is False
        assert metadata.has_previous is True
