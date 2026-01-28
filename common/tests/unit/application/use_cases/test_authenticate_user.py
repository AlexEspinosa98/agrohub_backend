"""
Unit tests for AuthenticateUserUseCase.

Tests use case orchestration and business logic specific to user authentication.
"""

from datetime import UTC, datetime
from typing import Any

import pytest

from common.application import use_cases as common_use_cases
from common.domain import (
    aggregates as common_aggregates,
    entities as common_entities,
    enums as common_enums,
    exceptions as common_exceptions,
    repositories as common_repositories,
    value_objects as common_value_objects,
)
from common.tests.unit.domain.entities import builders as common_entities_builders


class TestAuthenticateUserUseCase:
    """Test cases for AuthenticateUserUseCase."""

    @pytest.fixture
    def fake_repository(self) -> common_repositories.AuthenticationRepository:
        """Create fake authentication repository with in-memory storage."""

        return common_repositories.FakeAuthenticationRepository()

    @pytest.fixture
    def secret_key(self) -> str:
        """Valid secret key for testing."""
        return "test_secret_key_123"

    @pytest.fixture
    def use_case(
        self,
        fake_repository: common_repositories.AuthenticationRepository,
        secret_key: str,
    ) -> common_use_cases.AuthenticateUserUseCase:
        """Create use case instance with fake repository."""

        return common_use_cases.AuthenticateUserUseCase(
            authentication_repository=fake_repository, secret_key=secret_key
        )

    @pytest.fixture
    def valid_raw_token(self, secret_key: str) -> str:
        """Valid raw JWT token for testing."""
        from datetime import timedelta

        import jwt

        payload: dict[str, Any] = {
            "user_id": 123,
            "exp": datetime.now(UTC) + timedelta(hours=1),
        }
        return jwt.encode(payload, secret_key, algorithm="HS256")

    def test_authenticate_user_use_case_successful_authentication(
        self,
        use_case: common_use_cases.AuthenticateUserUseCase,
        fake_repository: common_repositories.AuthenticationRepository,
        valid_raw_token: str,
        sample_authenticated_user: common_entities.AuthenticatedUser,
    ) -> None:
        """Test successful user authentication flow."""
        # Arrange
        fake_repository.save(sample_authenticated_user)

        # Act
        result: common_aggregates.AuthenticationAggregate = use_case.execute(
            raw_token=valid_raw_token
        )

        # Assert
        assert isinstance(result, common_aggregates.AuthenticationAggregate)
        assert result.user.id == 123
        assert result.user.email == sample_authenticated_user.email
        assert isinstance(result.token, common_value_objects.AuthenticationToken)

    def test_authenticate_user_use_case_user_not_found(
        self,
        use_case: common_use_cases.AuthenticateUserUseCase,
        fake_repository: common_repositories.AuthenticationRepository,
        valid_raw_token: str,
    ) -> None:
        """Test authentication failure when user is not found."""
        # Arrange - Don't save any user to repository

        # Act & Assert
        with pytest.raises(common_exceptions.UserNotFoundException) as exc_info:
            use_case.execute(raw_token=valid_raw_token)

        assert exc_info.value.user_id == 123

    def test_authenticate_user_use_case_invalid_user_status(
        self,
        use_case: common_use_cases.AuthenticateUserUseCase,
        fake_repository: common_repositories.AuthenticationRepository,
        valid_raw_token: str,
    ) -> None:
        """Test authentication failure when user is deleted."""
        # Arrange
        create_user: common_entities.AuthenticatedUser = (
            common_entities_builders.AuthenticatedUserBuilder()
            .with_status(common_enums.UserStatus.DELETED)
            .build()
        )

        fake_repository.save(create_user)

        # Act & Assert
        with pytest.raises(common_exceptions.InvalidUserStatusException):
            use_case.execute(raw_token=valid_raw_token)

    def test_authenticate_user_use_case_invalid_token_propagates_exception(
        self, use_case: common_use_cases.AuthenticateUserUseCase
    ) -> None:
        """Test that invalid token exceptions are propagated from value object."""
        # Act & Assert - Should propagate exception from AuthenticationToken
        with pytest.raises(common_exceptions.InvalidTokenException):
            use_case.execute(raw_token="")

    def test_authenticate_user_use_case_token_extraction_failure_propagates(
        self, use_case: common_use_cases.AuthenticateUserUseCase
    ) -> None:
        """Test that token extraction failures are propagated."""
        # Arrange
        malformed_token = "malformed.jwt.token"

        # Act & Assert - Should propagate exception from token.extract_user_id()
        with pytest.raises(
            common_exceptions.authentication_exceptions.InvalidTokenException
        ):
            use_case.execute(raw_token=malformed_token)

    def test_authenticate_user_use_case_immutable_inputs(
        self,
        use_case: common_use_cases.AuthenticateUserUseCase,
        fake_repository: common_repositories.AuthenticationRepository,
        sample_authenticated_user: common_entities.AuthenticatedUser,
        secret_key: str,
    ) -> None:
        """Test that use case doesn't modify input parameters."""
        # Arrange
        from datetime import timedelta

        import jwt

        original_token: str = jwt.encode(
            {"user_id": 123, "exp": datetime.now(UTC) + timedelta(hours=1)},
            secret_key,
            algorithm="HS256",
        )

        fake_repository.save(sample_authenticated_user)

        # Act
        result: common_aggregates.AuthenticationAggregate = use_case.execute(
            raw_token=original_token
        )

        # Assert - Input should remain unchanged
        assert result.token.raw_token == original_token
        # Repository should maintain data integrity
        assert fake_repository.get_by_id(123) == sample_authenticated_user
