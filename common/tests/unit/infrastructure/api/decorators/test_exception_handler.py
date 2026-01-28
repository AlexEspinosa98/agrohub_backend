"""
Unit tests for exception handler decorator.

Tests exception handling and HTTP response mapping.
"""

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError
import pytest

from common.infrastructure.api import decorators


class TestModel(BaseModel):
    """Test model for validation testing."""

    name: str
    age: int


# Test functions decorated with handle_exceptions
@decorators.handle_exceptions
def function_normal() -> dict[str, str]:
    """Test function that returns normally."""
    return {"message": "success"}


@decorators.handle_exceptions
def function_validation_error() -> None:
    """Test function that raises ValidationError."""
    try:
        TestModel()  # Missing required fields
    except ValidationError as e:
        raise e


@decorators.handle_exceptions
def function_unexpected_error() -> None:
    """Test function that raises unexpected exception."""
    raise ValueError("Unexpected error")


class TestExceptionHandler:
    """Test cases for exception handler decorator."""

    def test_normal_execution(self) -> None:
        """Test normal execution without exceptions."""
        # Act
        result: dict[str, str] = function_normal()

        # Assert
        assert result == {"message": "success"}

    def test_validation_error_handling(self) -> None:
        """Test handling of Pydantic ValidationError."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            function_validation_error()

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["message"] == "Input validation failed"
        assert exc_info.value.detail["error_code"] == "VALIDATION_ERROR"
        assert "field_errors" in exc_info.value.detail

    def test_unexpected_exception_handling(self) -> None:
        """Test handling of unexpected exceptions."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            function_unexpected_error()

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["message"] == "Invalid input value"
        assert exc_info.value.detail["error_code"] == "VALUE_ERROR"
        assert "Unexpected error" in exc_info.value.detail["details"]
