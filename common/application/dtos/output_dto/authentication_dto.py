from datetime import datetime

from common.application import dtos as common_dtos
from common.domain import enums as common_enums


class AuthenticatedUserDTO(common_dtos.BaseDTO):
    """
    DTO for authenticated user information.

    Contains only the necessary information for API responses
    without exposing internal domain structure.

    This is a pure data structure - no business logic here.
    """

    user_id: int
    email: str
    user_status: common_enums.UserStatus
    created_at: datetime
    last_login: datetime | None = None
    is_premium: bool
