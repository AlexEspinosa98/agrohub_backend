"""
User validation service for common user-related business rules.

This service encapsulates domain validation logic for user operations
that are shared across different bounded contexts.
"""

from logging import Logger

from common.application.dtos import output_dto as common_output_dtos
from common.domain import enums as common_enums, exceptions as common_exceptions
from common.infrastructure.logging.config import get_logger


_LOGGER: Logger = get_logger(__name__)


class UserValidationService:
    """
    Domain service for user validation operations.

    Provides centralized validation logic for user-related business rules
    that are shared across different modules and bounded contexts.
    """

    def validate_user_is_active(
        self, user: common_output_dtos.AuthenticatedUserDTO
    ) -> None:
        """
        Validate that user is in active status.

        Args:
            user: Authenticated user DTO

        Raises:
            UserNotActiveException: If user is not in active status
        """
        _LOGGER.info(
            f"Validating user active status - user_id: [{user.user_id}], status: [{user.user_status.value}]"
        )

        if user.user_status != common_enums.UserStatus.ACTIVE:
            _LOGGER.warning(
                f"User is not active - user_id: [{user.user_id}], "
                f"current_status: [{user.user_status.value}], "
                f"required_status: [{common_enums.UserStatus.ACTIVE.value}] - "
                f"User attempting to perform operation with inactive status"
            )
            raise common_exceptions.UserNotActiveException(
                user_id=user.user_id, status=user.user_status
            )

        _LOGGER.info(
            f"User active status validated - user_id: [{user.user_id}] - status: [{user.user_status.value}]"
        )

    def validate_user_is_premium(
        self, user: common_output_dtos.AuthenticatedUserDTO
    ) -> None:
        """
        Validate that user has premium subscription.

        Args:
            user: Authenticated user DTO

        Raises:
            UserNotPremiumException: If user doesn't have premium subscription
        """
        _LOGGER.info(
            f"Validating user premium status - user_id: [{user.user_id}], is_premium: [{user.is_premium}]"
        )

        if not user.is_premium:
            _LOGGER.warning(
                f"User is not premium - user_id: [{user.user_id}], "
                f"is_premium: [{user.is_premium}] - "
                f"User attempting to access premium-only feature"
            )
            raise common_exceptions.UserNotPremiumException(user_id=user.user_id)

        _LOGGER.info(f"User premium status validated - user_id: [{user.user_id}]")
