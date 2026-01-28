"""
Generic API response DTOs for infrastructure layer.

Provides consistent response structure across all API endpoints.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel


ApplicationDataType = TypeVar("ApplicationDataType")


class ApiResponseDTO(BaseModel, Generic[ApplicationDataType]):
    """
    Generic API response wrapper for consistent response structure.

    This DTO wraps any application layer response in a standard API format
    with data, message, and success fields.

    Type Parameters:
        ApplicationDataType: The type of data returned from the application layer
    """

    data: ApplicationDataType
    message: str
    success: bool = True

    @classmethod
    def success_response(
        cls,
        data: ApplicationDataType,
        message: str = "Operation completed successfully",
    ) -> "ApiResponseDTO[ApplicationDataType]":
        """Create a successful API response."""
        return cls(data=data, message=message, success=True)
