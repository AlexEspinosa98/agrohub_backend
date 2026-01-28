"""
Unit tests for pagination DTOs.

Tests validation, factory methods, and edge cases for pagination components.
"""

from pydantic import ValidationError
import pytest

from common.application.dtos import input_dto as common_input_dto
from common.domain import enums as common_enums


class TestPaginationInputDTO:
    """Tests for PaginationInputDTO validation and functionality."""

    def test_default_values(self) -> None:
        """Test default pagination values are correctly set."""
        # Act
        pagination = common_input_dto.PaginationInputDTO()

        # Assert
        assert pagination.page == 1
        assert pagination.limit == 10

    def test_valid_custom_values(self) -> None:
        """Test creating pagination with valid custom values."""
        # Act
        pagination = common_input_dto.PaginationInputDTO(page=5, limit=25)

        # Assert
        assert pagination.page == 5
        assert pagination.limit == 25

    def test_page_must_be_positive(self) -> None:
        """Test that page number must be greater than 0."""
        # Test zero page
        with pytest.raises(ValidationError) as exc_info:
            common_input_dto.PaginationInputDTO(page=0)

        assert "greater than or equal to 1" in str(exc_info.value)

        # Test negative page
        with pytest.raises(ValidationError) as exc_info:
            common_input_dto.PaginationInputDTO(page=-1)

        assert "greater than or equal to 1" in str(exc_info.value)

    def test_limit_validation_boundaries(self) -> None:
        """Test limit validation at boundaries."""
        # Valid boundaries
        common_input_dto.PaginationInputDTO(page=1, limit=1)  # Min valid
        common_input_dto.PaginationInputDTO(page=1, limit=100)  # Max valid

        # Invalid boundaries
        with pytest.raises(ValidationError):
            common_input_dto.PaginationInputDTO(page=1, limit=0)  # Below min

        with pytest.raises(ValidationError):
            common_input_dto.PaginationInputDTO(page=1, limit=101)  # Above max

    @pytest.mark.parametrize(
        "page, limit, expected_offset",
        [
            (1, 10, 0),  # First page
            (2, 10, 10),  # Second page
            (3, 25, 50),  # Third page with different limit
            (5, 5, 20),  # Fifth page with small limit
        ],
    )
    def test_calculate_offset(
        self, page: int, limit: int, expected_offset: int
    ) -> None:
        """Test offset calculation for database queries."""
        pagination = common_input_dto.PaginationInputDTO(page=page, limit=limit)
        assert pagination.calculate_offset() == expected_offset

    def test_property_offset(self) -> None:
        """Test that offset property returns correct value."""
        pagination = common_input_dto.PaginationInputDTO(page=3, limit=15)
        assert pagination.offset == 30 == pagination.calculate_offset()

    def test_as_pagination_spec(self) -> None:
        """Test extracting pagination spec from composite DTO."""
        pagination = common_input_dto.PaginationInputDTO(page=2, limit=20)
        spec: common_input_dto.PaginationInputDTO = pagination.as_pagination_spec()

        assert isinstance(spec, common_input_dto.PaginationInputDTO)
        assert spec.page == 2
        assert spec.limit == 20
        assert spec.sort_by == "created_at"
        assert spec.sort_direction == common_enums.SortDirection.DESC

    def test_sort_by_default_value(self) -> None:
        """Test that sort_by has correct default value."""
        # Act
        pagination = common_input_dto.PaginationInputDTO()

        # Assert
        assert pagination.sort_by == "created_at"

    def test_sort_by_custom_value(self) -> None:
        """Test setting custom sort_by value."""
        # Act
        pagination = common_input_dto.PaginationInputDTO(sort_by="updated_at")

        # Assert
        assert pagination.sort_by == "updated_at"

    def test_sort_by_none_value(self) -> None:
        """Test setting sort_by to None."""
        # Act
        pagination = common_input_dto.PaginationInputDTO(sort_by=None)

        # Assert
        assert pagination.sort_by is None

    def test_sort_direction_default_value(self) -> None:
        """Test that sort_direction has correct default value."""
        # Act
        pagination = common_input_dto.PaginationInputDTO()

        # Assert
        assert pagination.sort_direction == common_enums.SortDirection.DESC

    def test_sort_direction_asc(self) -> None:
        """Test setting sort_direction to ASC."""
        # Act
        pagination = common_input_dto.PaginationInputDTO(
            sort_direction=common_enums.SortDirection.ASC
        )

        # Assert
        assert pagination.sort_direction == common_enums.SortDirection.ASC

    def test_sort_direction_desc(self) -> None:
        """Test setting sort_direction to DESC."""
        # Act
        pagination = common_input_dto.PaginationInputDTO(
            sort_direction=common_enums.SortDirection.DESC
        )

        # Assert
        assert pagination.sort_direction == common_enums.SortDirection.DESC

    def test_sort_direction_none_value(self) -> None:
        """Test setting sort_direction to None."""
        # Act
        pagination = common_input_dto.PaginationInputDTO(sort_direction=None)

        # Assert
        assert pagination.sort_direction is None

    def test_complete_sorting_configuration(self) -> None:
        """Test creating pagination with complete sorting configuration."""
        # Act
        pagination = common_input_dto.PaginationInputDTO(
            page=3,
            limit=25,
            sort_by="name",
            sort_direction=common_enums.SortDirection.ASC,
        )

        # Assert
        assert pagination.page == 3
        assert pagination.limit == 25
        assert pagination.sort_by == "name"
        assert pagination.sort_direction == common_enums.SortDirection.ASC
        assert pagination.offset == 50

    def test_as_pagination_spec_with_sorting(self) -> None:
        """Test extracting pagination spec preserves sorting configuration."""
        # Arrange
        pagination = common_input_dto.PaginationInputDTO(
            page=2,
            limit=20,
            sort_by="updated_at",
            sort_direction=common_enums.SortDirection.ASC,
        )

        # Act
        spec: common_input_dto.PaginationInputDTO = pagination.as_pagination_spec()

        # Assert
        assert isinstance(spec, common_input_dto.PaginationInputDTO)
        assert spec.page == 2
        assert spec.limit == 20
        assert spec.sort_by == "updated_at"
        assert spec.sort_direction == common_enums.SortDirection.ASC

    @pytest.mark.parametrize(
        "sort_by, sort_direction",
        [
            ("created_at", common_enums.SortDirection.DESC),
            ("updated_at", common_enums.SortDirection.ASC),
            ("name", common_enums.SortDirection.DESC),
            ("id", common_enums.SortDirection.ASC),
            (None, None),
            ("title", None),
            (None, common_enums.SortDirection.DESC),
        ],
    )
    def test_various_sorting_combinations(
        self,
        sort_by: str | None,
        sort_direction: common_enums.SortDirection | None,
    ) -> None:
        """Test various combinations of sort_by and sort_direction."""
        # Act
        pagination = common_input_dto.PaginationInputDTO(
            sort_by=sort_by, sort_direction=sort_direction
        )

        # Assert
        assert pagination.sort_by == sort_by
        assert pagination.sort_direction == sort_direction

    def test_invalid_sort_direction_string(self) -> None:
        """Test that invalid sort_direction string raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            common_input_dto.PaginationInputDTO(sort_direction="invalid")

        assert "Input should be" in str(exc_info.value)

    def test_sort_by_empty_string(self) -> None:
        """Test behavior with empty string for sort_by."""
        # Act
        pagination = common_input_dto.PaginationInputDTO(sort_by="")

        # Assert
        assert pagination.sort_by == ""

    def test_sort_by_whitespace_string(self) -> None:
        """Test behavior with whitespace-only string for sort_by."""
        # Act
        pagination = common_input_dto.PaginationInputDTO(sort_by="   ")

        # Assert
        assert pagination.sort_by == "   "
