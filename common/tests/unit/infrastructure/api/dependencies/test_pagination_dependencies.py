"""
Unit tests for pagination FastAPI dependencies.

Tests the dependency functions that extract pagination parameters from query strings.
"""

from common.application.dtos import input_dto as common_input_dto
from common.infrastructure.api.dependencies import pagination_dependencies


class TestGetPaginationParams:
    """Test cases for get_pagination_params dependency."""

    def test_default_parameters(self) -> None:
        """Test dependency with default parameters."""
        # Act - Call the function directly with no arguments (using defaults)
        result: common_input_dto.PaginationInputDTO = (
            pagination_dependencies.get_pagination_params()
        )

        # Assert
        assert isinstance(result, common_input_dto.PaginationInputDTO)
        assert result.page == 1
        assert result.limit == 10

    def test_custom_parameters(self) -> None:
        """Test dependency with custom parameters."""
        # Act - Call with explicit values
        result: common_input_dto.PaginationInputDTO = (
            pagination_dependencies.get_pagination_params(page=5, limit=25)
        )

        # Assert
        assert result.page == 5
        assert result.limit == 25

    def test_boundary_values(self) -> None:
        """Test dependency with boundary values."""
        # Test minimum values
        result_1: common_input_dto.PaginationInputDTO = (
            pagination_dependencies.get_pagination_params(page=1, limit=1)
        )
        assert result_1.page == 1
        assert result_1.limit == 1

        # Test maximum limit
        result_2: common_input_dto.PaginationInputDTO = (
            pagination_dependencies.get_pagination_params(page=100, limit=100)
        )
        assert result_2.page == 100
        assert result_2.limit == 100

    def test_calculates_offset_correctly(self) -> None:
        """Test that returned DTO can calculate offset correctly."""
        # Act
        result: common_input_dto.PaginationInputDTO = (
            pagination_dependencies.get_pagination_params(page=3, limit=15)
        )

        # Assert
        assert result.calculate_offset() == 30  # (3-1) * 15


class TestGetOptionalPaginationParams:
    """Test cases for get_optional_pagination_params dependency."""

    def test_no_parameters_returns_none(self) -> None:
        """Test that no parameters returns None."""
        # Act - Call with no arguments (None defaults)
        result: common_input_dto.PaginationInputDTO | None = (
            pagination_dependencies.get_optional_pagination_params()
        )

        # Assert
        assert result is None

    def test_only_page_parameter(self) -> None:
        """Test with only page parameter provided."""
        # Act
        result: common_input_dto.PaginationInputDTO | None = (
            pagination_dependencies.get_optional_pagination_params(page=3)
        )

        # Assert
        assert result is not None
        assert result.page == 3
        assert result.limit == 10  # Default limit

    def test_only_limit_parameter(self) -> None:
        """Test with only limit parameter provided."""
        # Act
        result: common_input_dto.PaginationInputDTO | None = (
            pagination_dependencies.get_optional_pagination_params(limit=25)
        )

        # Assert
        assert result is not None
        assert result.page == 1  # Default page
        assert result.limit == 25

    def test_both_parameters(self) -> None:
        """Test with both parameters provided."""
        # Act
        result: common_input_dto.PaginationInputDTO | None = (
            pagination_dependencies.get_optional_pagination_params(page=2, limit=15)
        )

        # Assert
        assert result is not None
        assert result.page == 2
        assert result.limit == 15

    def test_none_values_handled_correctly(self) -> None:
        """Test that explicit None values are handled correctly."""
        # Both None should return None
        result: common_input_dto.PaginationInputDTO | None = (
            pagination_dependencies.get_optional_pagination_params(
                page=None, limit=None
            )
        )
        assert result is None


class TestDependencyIntegration:
    """Test dependency integration scenarios."""

    def test_dependencies_return_same_type(self) -> None:
        """Test that both dependencies return compatible types."""
        # Act
        required_result: common_input_dto.PaginationInputDTO = (
            pagination_dependencies.get_pagination_params()
        )
        optional_result: common_input_dto.PaginationInputDTO | None = (
            pagination_dependencies.get_optional_pagination_params(page=1, limit=10)
        )

        # Assert
        assert type(required_result) == type(optional_result)
        assert required_result.page == optional_result.page
        assert required_result.limit == optional_result.limit

    def test_optional_dependency_defaults_match_required(self) -> None:
        """Test that optional dependency defaults match required dependency."""
        # Act
        required_result: common_input_dto.PaginationInputDTO = (
            pagination_dependencies.get_pagination_params()
        )
        optional_result: common_input_dto.PaginationInputDTO | None = (
            pagination_dependencies.get_optional_pagination_params(page=1, limit=10)
        )

        # Assert
        assert type(required_result) == type(optional_result)
        assert required_result.page == optional_result.page
        assert required_result.limit == optional_result.limit
