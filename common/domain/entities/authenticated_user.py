from datetime import datetime

from pydantic import Field

from common.domain import (
    entities as common_entities,
    enums as common_enums,
)


class AuthenticatedUser(common_entities.BaseEntity):
    email: str = Field(description="User email address")
    user_status: common_enums.UserStatus = Field(description="Current user status")
    last_login: datetime | None = Field(None, description="Last login timestamp")
    is_premium: bool = Field(default=False, description="Is user a premium member")

    @property
    def is_user_active(self) -> bool:
        """Check if user is active."""
        return self.user_status == common_enums.UserStatus.ACTIVE.value

    @property
    def is_user_created(self) -> bool:
        """Check if user is created."""
        return self.user_status == common_enums.UserStatus.CREATED.value

    @property
    def is_user_locked(self) -> bool:
        """Check if user is locked."""
        return self.user_status == common_enums.UserStatus.LOCKED.value

    @property
    def is_user_deleted(self) -> bool:
        """Check if user is deleted."""
        return self.user_status == common_enums.UserStatus.DELETED.value

    def can_access_resource(self, resource_owner_id: int) -> bool:
        """
        Check if user can access a resource owned by another user.
        Basic implementation - can be extended for more complex authorization.
        """
        return self.id == resource_owner_id

    def update_last_login(self) -> None:
        """Update the last login timestamp."""
        self.last_login = datetime.now()
        self.mark_as_updated()
