"""
Unit tests for AuthenticationService.

Tests service orchestration and coordination logic.
"""

from datetime import UTC, datetime
from typing import Any

import pytest

from common.application.dtos import output_dto as common_output_dto
from common.application.services.authentication_service import AuthenticationService
from common.domain import (
    entities as common_entities,
    exceptions as common_exceptions,
    repositories as common_repositories,
)


class TestAuthenticationService:
    """Test cases for AuthenticationService."""

    @pytest.fixture
    def fake_repository(self) -> common_repositories.AuthenticationRepository:
        """Create fake authentication repository with in-memory storage."""

        return common_repositories.FakeAuthenticationRepository()

    @pytest.fixture
    def secret_key(self) -> str:
        """Valid secret key for testing."""
        return "test_secret_key_123"

    @pytest.fixture
    def authentication_service(
        self,
        fake_repository: common_repositories.AuthenticationRepository,
        secret_key: str,
    ) -> AuthenticationService:
        """Create authentication service with fake repository."""
        return AuthenticationService(
            authentication_repository=fake_repository, secret_key=secret_key
        )

    @pytest.fixture
    def valid_token(self, secret_key: str) -> str:
        """Create valid JWT token."""
        from datetime import timedelta

        import jwt

        payload: dict[str, Any] = {
            "user_id": 123,
            "exp": datetime.now(UTC) + timedelta(hours=1),
        }
        return jwt.encode(payload, secret_key, algorithm="HS256")

    def test_authenticate_user_from_token_success(
        self,
        authentication_service: AuthenticationService,
        fake_repository: common_repositories.AuthenticationRepository,
        valid_token: str,
        sample_authenticated_user: common_entities.AuthenticatedUser,
    ) -> None:
        """Test successful authentication returns DTO."""
        # Arrange
        fake_repository.save(sample_authenticated_user)

        # Act
        result: common_output_dto.AuthenticatedUserDTO = (
            authentication_service.authenticate_user_from_token(raw_token=valid_token)
        )

        # Assert
        assert isinstance(result, common_output_dto.AuthenticatedUserDTO)
        assert result.user_id == 123
        assert result.email == sample_authenticated_user.email
        assert result.user_status.value == sample_authenticated_user.user_status
        assert result.created_at == sample_authenticated_user.created_at
        assert result.last_login == sample_authenticated_user.last_login
        assert result.is_premium == sample_authenticated_user.is_premium

    def test_authenticate_user_from_token_user_not_found(
        self, authentication_service: AuthenticationService, valid_token: str
    ) -> None:
        """Test authentication failure when user not found."""
        # Act & Assert
        with pytest.raises(common_exceptions.UserNotFoundException):
            authentication_service.authenticate_user_from_token(raw_token=valid_token)

    def test_authenticate_user_from_token_invalid_token(
        self, authentication_service: AuthenticationService
    ) -> None:
        """Test authentication failure with invalid token."""
        # Act & Assert
        with pytest.raises(common_exceptions.InvalidTokenException):
            authentication_service.authenticate_user_from_token(raw_token="")

    def test_authenticate_user_from_token_optional_with_valid_token(
        self,
        authentication_service: AuthenticationService,
        fake_repository: common_repositories.AuthenticationRepository,
        valid_token: str,
        sample_authenticated_user: common_entities.AuthenticatedUser,
    ) -> None:
        """Test optional authentication with valid token."""
        # Arrange
        fake_repository.save(sample_authenticated_user)

        # Act
        result: common_output_dto.AuthenticatedUserDTO | None = (
            authentication_service.authenticate_user_from_token_optional(
                raw_token=valid_token
            )
        )

        # Assert
        assert isinstance(result, common_output_dto.AuthenticatedUserDTO)
        assert result.user_id == 123
        assert result.email == sample_authenticated_user.email
        assert result.user_status.value == sample_authenticated_user.user_status
        assert result.created_at == sample_authenticated_user.created_at
        assert result.last_login == sample_authenticated_user.last_login

    def test_authenticate_user_from_token_optional_with_none_token(
        self, authentication_service: AuthenticationService
    ) -> None:
        """Test optional authentication with None token returns None."""
        # Act
        result: common_output_dto.AuthenticatedUserDTO | None = (
            authentication_service.authenticate_user_from_token_optional(raw_token=None)
        )

        # Assert
        assert result is None

    def test_authenticate_user_from_token_optional_with_empty_token(
        self, authentication_service: AuthenticationService
    ) -> None:
        """Test optional authentication with empty token returns None."""
        # Act
        result: common_output_dto.AuthenticatedUserDTO | None = (
            authentication_service.authenticate_user_from_token_optional(raw_token="")
        )

        # Assert
        assert result is None

    def test_authentication_service_dependency_injection(
        self,
        fake_repository: common_repositories.AuthenticationRepository,
        secret_key: str,
    ) -> None:
        """Test service properly manages dependencies."""
        # Act
        service = AuthenticationService(
            authentication_repository=fake_repository, secret_key=secret_key
        )

        # Assert
        assert service._authentication_repository == fake_repository
        assert service._secret_key == secret_key
        assert service._authenticate_user_use_case is not None
        assert service._mapper is not None
