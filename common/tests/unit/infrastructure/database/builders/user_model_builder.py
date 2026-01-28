"""
Builder for UserModel instances in tests.

This builder provides a fluent interface for creating UserModel instances
with sensible defaults and easy customization for testing purposes.
"""

from datetime import date, datetime
from typing import Optional

from common.domain import enums as common_enums
from common.infrastructure.database import models as common_database_models


class UserModelBuilder:
    """Builder for creating UserModel instances in tests."""

    def __init__(self) -> None:
        self._id: Optional[int] = None
        self._email: str = "test@example.com"
        self._password: str = "hashed_password"
        self._first_name: str = "Test"
        self._last_name: str = "User"
        self._phone_number: str = "1234567890"
        self._country_code: common_enums.CountryCodes = common_enums.CountryCodes.US
        self._zip_code: str = "12345"
        self._is_pregnant: bool = True
        self._user_type: common_enums.UserTypes = common_enums.UserTypes.SONA_MOM
        self._user_gender: Optional[common_enums.UserGenders] = (
            common_enums.UserGenders.FEMALE
        )
        self._user_status: common_enums.UserStatus = common_enums.UserStatus.ACTIVE
        self._birthdate: date = date(1990, 1, 1)
        self._last_login: Optional[datetime] = None
        self._last_login_failed: Optional[datetime] = None
        self._login_attempts: int = 0
        self._is_premium: bool = True
        self._user_role: common_enums.UserRoles = common_enums.UserRoles.USER
        self._address: Optional[str] = None
        self._city: Optional[str] = None
        self._state: Optional[str] = None
        self._terms_and_conditions: bool = True
        self._last_change_password: Optional[datetime] = None
        self._last_update_data: Optional[datetime] = None
        self._profile_picture: Optional[str] = None
        self._created_at: datetime = datetime.now()
        self._updated_at: datetime = datetime.now()
        self._deleted_at: Optional[datetime] = None

    def with_id(self, user_id: int) -> "UserModelBuilder":
        """Set user ID."""
        self._id = user_id
        return self

    def with_email(self, email: str) -> "UserModelBuilder":
        """Set email."""
        self._email = email
        return self

    def with_status(self, status: common_enums.UserStatus) -> "UserModelBuilder":
        """Set user status."""
        self._user_status = status
        return self

    def with_last_login(self, last_login: datetime) -> "UserModelBuilder":
        """Set last login."""
        self._last_login = last_login
        return self

    def with_first_name(self, first_name: str) -> "UserModelBuilder":
        """Set first name."""
        self._first_name = first_name
        return self

    def with_last_name(self, last_name: str) -> "UserModelBuilder":
        """Set last name."""
        self._last_name = last_name
        return self

    def with_user_type(self, user_type: common_enums.UserTypes) -> "UserModelBuilder":
        """Set user type."""
        self._user_type = user_type
        return self

    def as_premium(self) -> "UserModelBuilder":
        """Set user as premium."""
        self._is_premium = True
        return self

    def build(self) -> common_database_models.UserModel:
        """Build the UserModel instance."""
        return common_database_models.UserModel(
            id=self._id,
            email=self._email,
            password=self._password,
            first_name=self._first_name,
            last_name=self._last_name,
            phone_number=self._phone_number,
            country_code=self._country_code,
            zip_code=self._zip_code,
            is_pregnant=self._is_pregnant,
            user_type=self._user_type,
            user_gender=self._user_gender,
            user_status=self._user_status,
            birthdate=self._birthdate,
            last_login=self._last_login,
            last_login_failed=self._last_login_failed,
            login_attempts=self._login_attempts,
            is_premium=self._is_premium,
            user_role=self._user_role,
            address=self._address,
            city=self._city,
            state=self._state,
            terms_and_conditions=self._terms_and_conditions,
            last_change_password=self._last_change_password,
            last_update_data=self._last_update_data,
            profile_picture=self._profile_picture,
            created_at=self._created_at,
            updated_at=self._updated_at,
            deleted_at=self._deleted_at,
        )


class UserModelMotherBuilder:
    @staticmethod
    def active_user(user_id: int = 123) -> common_database_models.UserModel:
        """Create a standard active user."""
        return (
            UserModelBuilder()
            .with_id(user_id)
            .with_status(common_enums.UserStatus.ACTIVE)
            .build()
        )

    @staticmethod
    def inactive_user(user_id: int = 456) -> common_database_models.UserModel:
        """Create a standard inactive user."""
        return (
            UserModelBuilder()
            .with_id(user_id)
            .with_status(common_enums.UserStatus.CREATED)
            .build()
        )
