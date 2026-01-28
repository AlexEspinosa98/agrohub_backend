"""
Unit tests for PaginatedResult value object.

Tests the generic paginated domain result value object that encapsulates
pagination logic and invariants for domain entities.
"""

from common.domain import entities, value_objects


class MockEntity(entities.BaseEntity):
    """Mock entity for testing purposes."""

    id: int
    name: str


class TestPaginatedResult:
    """Test suite for PaginatedResult value object."""

    def test_create_valid_paginated_result(self) -> None:
        """Test creating a valid paginated result with items."""
        # Arrange
        items: list[MockEntity] = [
            MockEntity(id=1, name="Item 1"),
            MockEntity(id=2, name="Item 2"),
        ]
        total_count: int = 10

        # Act
        result: value_objects.PaginatedResult[MockEntity] = (
            value_objects.PaginatedResult(items=items, total_count=total_count)
        )

        # Assert
        assert result.items == items
        assert result.total_count == total_count
        assert len(result.items) == 2

    def test_create_empty_paginated_result(self) -> None:
        """Test creating an empty paginated result."""
        # Act
        result: value_objects.PaginatedResult[MockEntity] = (
            value_objects.PaginatedResult(items=[], total_count=0)
        )

        # Assert
        assert result.items == []
        assert result.total_count == 0
        assert len(result.items) == 0
