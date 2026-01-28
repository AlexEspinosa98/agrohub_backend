"""
Unit tests for AuthenticatedUser entity.

Tests authentication user domain logic specific to AuthenticatedUser.
"""

from datetime import datetime

import pytest

from common.domain import (
    entities as common_entities,
    enums as common_enums,
)
from common.tests.unit.domain.entities import builders as common_entities_builders


class TestAuthenticatedUser:
    """Test cases for AuthenticatedUser entity."""

    def test_authenticated_user_creation_with_required_fields(self) -> None:
        """Test that AuthenticatedUser can be created with required fields."""
        # Arrange
        user_id = 123
        email = "test@example.com"
        user_status = common_enums.UserStatus.ACTIVE.value

        # Act
        datetime_now: datetime = datetime.now()
        user: common_entities.AuthenticatedUser = (
            common_entities_builders.AuthenticatedUserBuilder()
            .with_id(user_id)
            .with_email(email)
            .with_status(user_status)
            .with_created_at(datetime_now)
            .with_updated_at(datetime_now)
            .build()
        )
        # Assert
        assert user.id == user_id
        assert user.created_at == datetime_now
        assert user.updated_at == datetime_now
        assert user.is_active is True
        assert user.deleted_at is None
        assert user.is_user_active is True
        assert user.email == email
        assert user.user_status == user_status
        assert user.last_login is None

    def test_get_identity_uses_user_id_value(
        self, sample_authenticated_user: common_entities.AuthenticatedUser
    ) -> None:
        """Test that get_identity returns user_id value (overrides base implementation)."""
        # Act & Assert
        assert sample_authenticated_user.get_identity() == 123
        assert sample_authenticated_user.get_identity() == sample_authenticated_user.id

    def test_authenticated_user_equality_based_on_user_id(self) -> None:
        """Test that AuthenticatedUser equality is based on user_id (inherited from BaseEntity)."""
        # Arrange
        user1: common_entities.AuthenticatedUser = (
            common_entities_builders.AuthenticatedUserMotherBuilder.active_user(
                user_id=1
            )
        )
        user2: common_entities.AuthenticatedUser = (
            common_entities_builders.AuthenticatedUserMotherBuilder.active_user(
                user_id=1
            )
        )

        # Act & Assert
        assert user1 == user2  # Should be equal because same user_id

    def test_is_user_active_property_when_active(self) -> None:
        """Test is_user_active property when user status is ACTIVE."""
        # Arrange
        user: common_entities.AuthenticatedUser = (
            common_entities_builders.AuthenticatedUserMotherBuilder.active_user()
        )

        # Act & Assert
        assert user.is_user_active is True

    def test_is_user_active_property_when_not_active(self) -> None:
        """Test is_user_active property when user status is not ACTIVE."""
        # Arrange
        user: common_entities.AuthenticatedUser = (
            common_entities_builders.AuthenticatedUserMotherBuilder.created_user()
        )

        # Act & Assert
        assert user.is_user_active is False

    @pytest.mark.parametrize(
        "user_status,expected_active,expected_created,expected_locked,expected_deleted",
        [
            (common_enums.UserStatus.ACTIVE, True, False, False, False),
            (common_enums.UserStatus.CREATED, False, True, False, False),
            (common_enums.UserStatus.LOCKED, False, False, True, False),
            (common_enums.UserStatus.DELETED, False, False, False, True),
        ],
    )
    def test_status_properties_with_various_statuses(
        self,
        user_status: common_enums.UserStatus,
        expected_active: bool,
        expected_created: bool,
        expected_locked: bool,
        expected_deleted: bool,
    ) -> None:
        """Test all status check properties with various user statuses."""
        # Arrange
        user: common_entities.AuthenticatedUser = (
            common_entities_builders.AuthenticatedUserBuilder()
            .with_status(status=user_status)
            .build()
        )

        # Act & Assert
        assert user.is_user_active == expected_active
        assert user.is_user_created == expected_created
        assert user.is_user_locked == expected_locked
        assert user.is_user_deleted == expected_deleted

    def test_can_access_resource_own_resource(
        self, sample_authenticated_user: common_entities.AuthenticatedUser
    ) -> None:
        """Test that user can access their own resources."""
        # Act & Assert
        assert (
            sample_authenticated_user.can_access_resource(
                resource_owner_id=sample_authenticated_user.id
            )
            is True
        )

    def test_can_access_resource_other_user_resource(
        self, sample_authenticated_user: common_entities.AuthenticatedUser
    ) -> None:
        """Test that user cannot access other user's resources."""
        # Act & Assert
        assert (
            sample_authenticated_user.can_access_resource(resource_owner_id=456)
            is False
        )

    def test_update_last_login_functionality(
        self, sample_authenticated_user: common_entities.AuthenticatedUser
    ) -> None:
        """Test updating last login timestamp."""
        # Arrange
        original_updated_at: datetime = sample_authenticated_user.updated_at
        assert sample_authenticated_user.last_login is None

        # Act
        sample_authenticated_user.update_last_login()

        # Assert
        assert sample_authenticated_user.last_login is not None
        assert sample_authenticated_user.last_login > original_updated_at
        assert sample_authenticated_user.updated_at > original_updated_at

    def test_authenticated_user_with_last_login_timestamp_simple(self) -> None:
        """Test authenticated user creation and last login update."""
        # Arrange
        user = common_entities.AuthenticatedUser(
            email="test@example.com",
            user_status=common_enums.UserStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_login=None,
            id=123,
        )

        assert user.last_login is None
        before_login: datetime = datetime.now()

        # Act
        user.update_last_login()

        # Assert
        assert user.last_login is not None
        assert (
            user.last_login >= before_login
        )  # Should be after or equal to before_login
        assert user.updated_at > user.last_login  # updated_at should match last_login
        assert (
            user.updated_at >= before_login
        )  # updated_at should be after or equal to before_login
        assert isinstance(user.last_login, datetime)

    def test_authenticated_user_email_validation_invalid_format(self) -> None:
        """Test that invalid email format raises validation error."""
        # Act & Assert - Invalid email formats should raise validation error
        with pytest.raises(ValueError):
            common_entities_builders.AuthenticatedUserBuilder().with_email(
                "not-an-email"
            ).build()

    def test_authenticated_user_email_validation_empty(self) -> None:
        """Test that empty email raises validation error."""
        # Act & Assert - Empty email should raise validation error
        with pytest.raises(ValueError):
            common_entities_builders.AuthenticatedUserBuilder().with_email("").build()

    @pytest.mark.parametrize(
        "invalid_email",
        [
            "not-an-email",
            "missing@",
            "@missing-local.com",
            "spaces @domain.com",
            "double@@domain.com",
        ],
    )
    def test_authenticated_user_email_validation_various_invalid_formats(
        self, invalid_email: str
    ) -> None:
        """Test various invalid email formats."""
        # Act & Assert
        with pytest.raises(ValueError):
            common_entities_builders.AuthenticatedUserBuilder().with_email(
                invalid_email
            ).build()

    @pytest.mark.parametrize(
        "valid_email",
        [
            "user@example.com",
            "test.email@domain.co.uk",
            "user+tag@example.org",
            "123@numbers.com",
        ],
    )
    def test_authenticated_user_email_validation_various_valid_formats(
        self, valid_email: str
    ) -> None:
        """Test various valid email formats."""
        # Act - Should not raise exception
        user: common_entities.AuthenticatedUser = (
            common_entities_builders.AuthenticatedUserBuilder()
            .with_email(valid_email)
            .build()
        )

        # Assert
        assert user.email == valid_email.lower()  # EmailStr normalizes to lowercase

    def test_authenticated_user_immutable_identity_across_updates(
        self, sample_authenticated_user: common_entities.AuthenticatedUser
    ) -> None:
        """Test that user identity remains consistent across updates."""
        # Arrange
        original_identity: int = sample_authenticated_user.get_identity()

        # Act - Perform updates
        sample_authenticated_user.update_last_login()
        sample_authenticated_user.email = "updated@example.com"

        # Assert
        assert (
            sample_authenticated_user.get_identity() == original_identity
        )  # Identity never changes
