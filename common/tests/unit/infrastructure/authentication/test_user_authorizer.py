"""
Unit tests for user_authorizer.

Tests authorization functions with mocked dependencies.
"""

from datetime import datetime
from unittest.mock import Mock

from fastapi import Request
import pytest


from common.application.dtos import output_dto as common_output_dto
from common.application.services import authentication_service
from common.domain import enums
from common.infrastructure.authentication import user_authorizer


class TestUserAuthorizer:
    """Test cases for user authorization functions."""

    @pytest.fixture
    def mock_request(self) -> Mock:
        """Create mock request."""
        request = Mock(spec=Request)
        request.headers = {"Authorization": "Bearer valid.jwt.token"}
        return request

    @pytest.fixture
    def mock_request_no_token(self) -> Mock:
        """Create mock request without token."""
        request = Mock(spec=Request)
        request.headers = {}
        return request

    @pytest.fixture
    def mock_auth_service(self) -> Mock:
        """Create mock authentication service."""
        return Mock(spec=authentication_service.AuthenticationService)

    @pytest.fixture
    def sample_user_dto(self) -> common_output_dto.AuthenticatedUserDTO:
        """Create sample user DTO."""
        return common_output_dto.AuthenticatedUserDTO(
            user_id=123,
            email="test@example.com",
            user_status=enums.UserStatus.ACTIVE,
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            last_login=None,
            is_premium=False,
        )

    def test_get_user_from_token_success(
        self,
        mock_request: Mock,
        mock_auth_service: Mock,
        sample_user_dto: common_output_dto.AuthenticatedUserDTO,
    ) -> None:
        """Test successful user authentication from token."""
        # Arrange
        mock_auth_service.authenticate_user_from_token.return_value = sample_user_dto

        # Act
        result: common_output_dto.AuthenticatedUserDTO = (
            user_authorizer.get_user_from_token(
                request=mock_request, authentication_service=mock_auth_service
            )
        )

        # Assert
        assert result == sample_user_dto
        mock_auth_service.authenticate_user_from_token.assert_called_once_with(
            raw_token="Bearer valid.jwt.token"
        )

    def test_get_user_from_token_extracts_token_correctly(
        self,
        mock_auth_service: Mock,
        sample_user_dto: common_output_dto.AuthenticatedUserDTO,
    ) -> None:
        """Test token extraction from request headers."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {"Authorization": "custom.token.here"}
        mock_auth_service.authenticate_user_from_token.return_value = sample_user_dto

        # Act
        user_authorizer.get_user_from_token(
            request=request, authentication_service=mock_auth_service
        )

        # Assert
        mock_auth_service.authenticate_user_from_token.assert_called_once_with(
            raw_token="custom.token.here"
        )

    def test_get_user_from_token_missing_header(
        self, mock_request_no_token: Mock, mock_auth_service: Mock
    ) -> None:
        """Test token extraction with missing Authorization header."""
        # Act
        user_authorizer.get_user_from_token(
            request=mock_request_no_token, authentication_service=mock_auth_service
        )

        # Assert - Should pass empty string when header is missing
        mock_auth_service.authenticate_user_from_token.assert_called_once_with(
            raw_token=""
        )

    def test_get_user_from_token_propagates_authentication_service_exceptions(
        self, mock_request: Mock, mock_auth_service: Mock
    ) -> None:
        """Test that authentication service exceptions are propagated."""
        # Arrange
        mock_auth_service.authenticate_user_from_token.side_effect = ValueError(
            "Invalid token"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid token"):
            user_authorizer.get_user_from_token(
                request=mock_request, authentication_service=mock_auth_service
            )

    def test_get_user_from_token_optional_success(
        self,
        mock_request: Mock,
        mock_auth_service: Mock,
        sample_user_dto: common_output_dto.AuthenticatedUserDTO,
    ) -> None:
        """Test successful optional authentication."""
        # Arrange
        mock_auth_service.authenticate_user_from_token_optional.return_value = (
            sample_user_dto
        )

        # Act
        result: common_output_dto.AuthenticatedUserDTO | None = (
            user_authorizer.get_user_from_token_optional(
                request=mock_request, authentication_service=mock_auth_service
            )
        )

        # Assert
        assert result == sample_user_dto

    def test_get_user_from_token_optional_propagates_non_http_exceptions(
        self, mock_request: Mock, mock_auth_service: Mock
    ) -> None:
        """Test optional authentication propagates non-HTTP exceptions."""
        # Arrange
        mock_auth_service.authenticate_user_from_token_optional.side_effect = (
            ValueError("Unexpected error")
        )

        # Act & Assert
        with pytest.raises(ValueError):
            user_authorizer.get_user_from_token_optional(
                request=mock_request, authentication_service=mock_auth_service
            )

    def test_get_current_user_delegates_to_get_user_from_token(
        self,
        mock_request: Mock,
        mock_auth_service: Mock,
        sample_user_dto: common_output_dto.AuthenticatedUserDTO,
    ) -> None:
        """Test get_current_user delegates to get_user_from_token."""
        # Arrange
        mock_auth_service.authenticate_user_from_token.return_value = sample_user_dto

        # Act
        result: common_output_dto.AuthenticatedUserDTO = (
            user_authorizer.get_current_user(
                request=mock_request, auth_service=mock_auth_service
            )
        )

        # Assert
        assert result == sample_user_dto
        mock_auth_service.authenticate_user_from_token.assert_called_once_with(
            raw_token="Bearer valid.jwt.token"
        )

    def test_get_current_user_optional_delegates_to_get_user_from_token_optional(
        self,
        mock_request: Mock,
        mock_auth_service: Mock,
        sample_user_dto: common_output_dto.AuthenticatedUserDTO,
    ) -> None:
        """Test get_current_user_optional delegates to get_user_from_token_optional."""
        # Arrange
        mock_auth_service.authenticate_user_from_token_optional.return_value = (
            sample_user_dto
        )

        # Act
        result: common_output_dto.AuthenticatedUserDTO | None = (
            user_authorizer.get_current_user_optional(
                request=mock_request, auth_service=mock_auth_service
            )
        )

        # Assert
        assert result == sample_user_dto
        mock_auth_service.authenticate_user_from_token_optional.assert_called_once_with(
            raw_token="Bearer valid.jwt.token"
        )

    def test_extract_token_from_request_private_function(self) -> None:
        """Test private token extraction function."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {"Authorization": "test.token.value"}

        # Act
        token: str = user_authorizer._extract_token_from_request(request)

        # Assert
        assert token == "test.token.value"

    def test_extract_token_from_request_missing_header(self) -> None:
        """Test private token extraction with missing header."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {}

        # Act
        token: str = user_authorizer._extract_token_from_request(request)

        # Assert
        assert token == ""
