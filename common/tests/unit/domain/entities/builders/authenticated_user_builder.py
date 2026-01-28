"""
Builder for AuthenticatedUser entity in tests.

Provides a fluent interface for creating AuthenticatedUser instances
with sensible defaults and easy customization for testing purposes.
"""

from datetime import datetime
from typing import Optional

from common.domain import (
    entities as common_entities,
    enums as common_enums,
)


class AuthenticatedUserBuilder:
    """Builder for creating AuthenticatedUser instances in tests."""

    def __init__(self) -> None:
        self._id: Optional[int] = 123
        self._email: str = "test@example.com"
        self._user_status: common_enums.UserStatus = common_enums.UserStatus.ACTIVE
        self._created_at: datetime = datetime.now()
        self._updated_at: datetime = datetime.now()
        self._last_login: Optional[datetime] = None
        self._is_premium: bool = False

    def with_id(self, user_id: int) -> "AuthenticatedUserBuilder":
        """Set user ID."""
        self._id = user_id
        return self

    def with_email(self, email: str) -> "AuthenticatedUserBuilder":
        """Set email."""
        self._email = email
        return self

    def with_status(
        self, status: common_enums.UserStatus
    ) -> "AuthenticatedUserBuilder":
        """Set user status."""
        self._user_status = status
        return self

    def with_last_login(self, last_login: datetime) -> "AuthenticatedUserBuilder":
        """Set last login."""
        self._last_login = last_login
        return self

    def with_created_at(self, created_at: datetime) -> "AuthenticatedUserBuilder":
        """Set created at timestamp."""
        self._created_at = created_at
        return self

    def with_updated_at(self, updated_at: datetime) -> "AuthenticatedUserBuilder":
        """Set updated at timestamp."""
        self._updated_at = updated_at
        return self

    def with_premium_status(self, is_premium: bool) -> "AuthenticatedUserBuilder":
        """Set premium status."""
        self._is_premium = is_premium
        return self

    def build(self) -> common_entities.AuthenticatedUser:
        """Build the AuthenticatedUser instance."""
        return common_entities.AuthenticatedUser(
            id=self._id,
            email=self._email,
            user_status=self._user_status,
            created_at=self._created_at,
            updated_at=self._updated_at,
            last_login=self._last_login,
            is_premium=self._is_premium,
        )


class AuthenticatedUserMotherBuilder:
    """Object Mother for creating common AuthenticatedUser instances."""

    @staticmethod
    def active_user(
        user_id: int = 123,
        email: str = "active@example.com",
    ) -> common_entities.AuthenticatedUser:
        """Create a standard active user."""
        return (
            AuthenticatedUserBuilder()
            .with_id(user_id)
            .with_email(email)
            .with_status(common_enums.UserStatus.ACTIVE)
            .build()
        )

    @staticmethod
    def created_user(
        user_id: int = 456,
        email: str = "created@example.com",
    ) -> common_entities.AuthenticatedUser:
        """Create a user with CREATED status (created)."""
        return (
            AuthenticatedUserBuilder()
            .with_id(user_id)
            .with_email(email)
            .with_status(common_enums.UserStatus.CREATED)
            .build()
        )

    @staticmethod
    def premium_user(
        user_id: int = 789,
        email: str = "premium@example.com",
    ) -> common_entities.AuthenticatedUser:
        """Create a user with PREMIUM status (premium)."""
        return (
            AuthenticatedUserBuilder()
            .with_id(user_id)
            .with_email(email)
            .with_status(common_enums.UserStatus.ACTIVE)
            .with_premium_status(True)
            .build()
        )
