"""
Unit tests for AuthenticationAggregate.

Tests aggregate composition and business logic.
"""

from datetime import datetime

import pytest

from common.domain import (
    aggregates as common_aggregates,
    entities as common_entities,
    enums as common_enums,
    exceptions as common_exceptions,
    value_objects as common_value_objects,
)
from common.tests.unit.domain.entities import builders as common_entity_builders


class TestAuthenticationAggregate:
    """Test cases for AuthenticationAggregate."""

    @pytest.fixture
    def sample_token(self) -> common_value_objects.AuthenticationToken:
        """Create a sample authentication token."""
        return common_value_objects.AuthenticationToken(raw_token="valid.jwt.token")

    def test_authentication_aggregate_creation(
        self,
        sample_authenticated_user: common_entities.AuthenticatedUser,
        sample_token: common_value_objects.AuthenticationToken,
    ) -> None:
        """Test that authentication aggregate can be created with user and token."""
        # Act
        aggregate = common_aggregates.AuthenticationAggregate(
            user=sample_authenticated_user, token=sample_token
        )

        # Assert
        assert aggregate.user == sample_authenticated_user
        assert aggregate.token == sample_token

    def test_authentication_aggregate_equality(
        self,
        sample_authenticated_user: common_entities.AuthenticatedUser,
        sample_token: common_value_objects.AuthenticationToken,
    ) -> None:
        """Test that aggregates with same user and token are equal."""
        # Arrange
        aggregate1 = common_aggregates.AuthenticationAggregate(
            user=sample_authenticated_user, token=sample_token
        )
        aggregate2 = common_aggregates.AuthenticationAggregate(
            user=sample_authenticated_user, token=sample_token
        )

        different_user: common_entities.AuthenticatedUser = (
            common_entity_builders.AuthenticatedUserBuilder()
            .with_email("different@example.com")
            .with_id(456)
            .build()
        )

        aggregate3 = common_aggregates.AuthenticationAggregate(
            user=different_user, token=sample_token
        )

        # Act & Assert
        assert aggregate1 == aggregate2
        assert aggregate1 != aggregate3

    def test_authentication_aggregate_with_different_tokens(
        self, sample_authenticated_user: common_entities.AuthenticatedUser
    ) -> None:
        """Test aggregate with different tokens."""
        # Arrange
        token1 = common_value_objects.AuthenticationToken(raw_token="token1")
        token2 = common_value_objects.AuthenticationToken(raw_token="token2")

        # Act
        aggregate1 = common_aggregates.AuthenticationAggregate(
            user=sample_authenticated_user, token=token1
        )
        aggregate2 = common_aggregates.AuthenticationAggregate(
            user=sample_authenticated_user, token=token2
        )

        # Assert
        assert aggregate1 != aggregate2
        assert aggregate1.user == aggregate2.user
        assert aggregate1.token != aggregate2.token

    def test_authentication_aggregate_business_logic_access(
        self,
        sample_authenticated_user: common_entities.AuthenticatedUser,
        sample_token: common_value_objects.AuthenticationToken,
    ) -> None:
        """Test accessing business logic through aggregate."""
        # Arrange
        aggregate = common_aggregates.AuthenticationAggregate(
            user=sample_authenticated_user, token=sample_token
        )

        # Act & Assert
        assert aggregate.user.is_active is True
        assert aggregate.user.can_access_resource(123) is True
        assert aggregate.user.can_access_resource(456) is False

    def test_authentication_aggregate_get_aggregate_id(
        self,
        sample_authenticated_user: common_entities.AuthenticatedUser,
        sample_token: common_value_objects.AuthenticationToken,
    ) -> None:
        """Test that get_aggregate_id returns user identity."""
        # Arrange
        aggregate = common_aggregates.AuthenticationAggregate(
            user=sample_authenticated_user, token=sample_token
        )

        # Act
        aggregate_id: int = aggregate.get_aggregate_id()

        # Assert
        assert aggregate_id == 123 == sample_authenticated_user.get_identity()

    def test_validate_invariants_with_inactive_user_raises_exception(
        self, sample_token: common_value_objects.AuthenticationToken
    ) -> None:
        """Test validate_invariants with inactive user raises exception."""
        # Arrange
        inactive_user: common_entities.AuthenticatedUser = (
            common_entity_builders.AuthenticatedUserMotherBuilder.created_user()
        )

        # Act & Assert
        with pytest.raises(common_exceptions.InvalidUserStatusException):
            common_aggregates.AuthenticationAggregate(
                user=inactive_user, token=sample_token
            )

    def test_is_valid_with_valid_aggregate(
        self,
        sample_authenticated_user: common_entities.AuthenticatedUser,
        sample_token: common_value_objects.AuthenticationToken,
    ) -> None:
        """Test is_valid returns True for valid aggregate."""
        # Arrange
        aggregate = common_aggregates.AuthenticationAggregate(
            user=sample_authenticated_user, token=sample_token
        )

        # Act
        result: bool = aggregate.is_valid()

        # Assert
        assert result is True

    def test_is_valid_with_invalid_aggregate(
        self, sample_token: common_value_objects.AuthenticationToken
    ) -> None:
        """Test is_valid returns False for invalid aggregate."""
        # This test requires mocking since we can't create an invalid aggregate
        # due to model_post_init validation
        # Arrange
        aggregate = common_aggregates.AuthenticationAggregate(
            user=common_entity_builders.AuthenticatedUserMotherBuilder.active_user(),
            token=sample_token,
        )

        # Act - Manually change user status to invalid after creation
        aggregate.user.user_status = common_enums.UserStatus.DELETED

        # Assert
        assert aggregate.is_valid() is False

    def test_get_user_id_returns_integer(
        self,
        sample_authenticated_user: common_entities.AuthenticatedUser,
        sample_token: common_value_objects.AuthenticationToken,
    ) -> None:
        """Test get_user_id returns user ID as integer."""
        # Arrange
        aggregate = common_aggregates.AuthenticationAggregate(
            user=sample_authenticated_user, token=sample_token
        )

        # Act
        user_id: int = aggregate.get_user_id()

        # Assert
        assert user_id == 123
        assert isinstance(user_id, int)
        assert user_id == sample_authenticated_user.id

    def test_refresh_authentication_updates_last_login(
        self,
        sample_authenticated_user: common_entities.AuthenticatedUser,
        sample_token: common_value_objects.AuthenticationToken,
    ) -> None:
        """Test refresh_authentication updates user's last login."""
        # Arrange
        aggregate = common_aggregates.AuthenticationAggregate(
            user=sample_authenticated_user, token=sample_token
        )
        original_updated_at: datetime = aggregate.user.updated_at
        assert aggregate.user.last_login is None

        # Act
        aggregate.refresh_authentication()

        # Assert
        assert aggregate.user.last_login is not None
        assert aggregate.user.last_login > original_updated_at
        assert aggregate.user.updated_at > original_updated_at

    def test_refresh_authentication_validates_invariants(
        self, sample_token: common_value_objects.AuthenticationToken
    ) -> None:
        """Test refresh_authentication validates invariants after update."""
        # Arrange
        aggregate = common_aggregates.AuthenticationAggregate(
            user=common_entity_builders.AuthenticatedUserMotherBuilder.active_user(),
            token=sample_token,
        )

        # Act - Change user status to invalid after creation
        aggregate.user.user_status = common_enums.UserStatus.DELETED

        # Assert - refresh_authentication should fail validation
        with pytest.raises(common_exceptions.InvalidUserStatusException):
            aggregate.refresh_authentication()

    @pytest.mark.parametrize(
        "user_status",
        [
            common_enums.UserStatus.CREATED,
            common_enums.UserStatus.LOCKED,
            common_enums.UserStatus.DELETED,
        ],
    )
    def test_validate_invariants_with_various_inactive_statuses(
        self,
        user_status: common_enums.UserStatus,
        sample_token: common_value_objects.AuthenticationToken,
    ) -> None:
        """Test validate_invariants with various inactive user statuses."""
        # Arrange
        inactive_user: common_entities.AuthenticatedUser = (
            common_entity_builders.AuthenticatedUserBuilder()
            .with_status(user_status)
            .build()
        )
        # Act & Assert
        with pytest.raises(common_exceptions.InvalidUserStatusException):
            common_aggregates.AuthenticationAggregate(
                user=inactive_user, token=sample_token
            )

    def test_authentication_aggregate_domain_consistency(
        self,
        sample_authenticated_user: common_entities.AuthenticatedUser,
        sample_token: common_value_objects.AuthenticationToken,
    ) -> None:
        """Test that aggregate maintains domain consistency."""
        # Arrange
        aggregate = common_aggregates.AuthenticationAggregate(
            user=sample_authenticated_user, token=sample_token
        )

        # Act & Assert - Domain consistency checks
        assert aggregate.get_aggregate_id() == aggregate.get_user_id()
        assert aggregate.is_valid() is True

        # Refresh should maintain consistency
        aggregate.refresh_authentication()
        assert aggregate.is_valid() is True
        assert aggregate.get_aggregate_id() == aggregate.get_user_id()
