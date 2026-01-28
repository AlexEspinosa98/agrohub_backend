from logging import Logger

from pydantic import ValidationError

from common.domain import (
    aggregates as common_aggregates,
    entities as common_entities,
    exceptions as common_exceptions,
    repositories as common_repositories,
    value_objects as common_value_objects,
)
from common.infrastructure.logging.config import get_logger


_LOGGER: Logger = get_logger(__name__)


class AuthenticateUserUseCase:
    """
    Use case for authenticating a user from a JWT token.

    This encapsulates the business logic for user authentication,
    ensuring all domain rules are enforced and returning a proper
    authentication result aggregate.
    """

    def __init__(
        self,
        authentication_repository: common_repositories.AuthenticationRepository,
        secret_key: str,
    ) -> None:
        """
        Initialize the use case.

        Args:
            authentication_repository (AuthenticationRepository): Repository for authentication data access
            secret_key (str): JWT secret key for token validation
        """
        self._authentication_repository: common_repositories.AuthenticationRepository = authentication_repository
        self._secret_key: str = secret_key

    def execute(self, raw_token: str) -> common_aggregates.AuthenticationAggregate:
        """
        Execute the authentication use case.

        Args:
            raw_token (str): Raw JWT token from request

        Returns:
            AuthenticationResult: Complete authentication result

        Raises:
            Various AuthenticationExceptions: If authentication fails at any step
        """
        _LOGGER.info("Creating AuthenticationToken from raw token")
        try:
            token = common_value_objects.AuthenticationToken(raw_token=raw_token)
        except ValidationError as e:
            _LOGGER.error(f"Invalid token format: [{e}]")
            raise common_exceptions.InvalidTokenException(
                f"The provided token format is invalid: [{e}]"
            )

        _LOGGER.info("Extracting user ID from token")
        user_id: int = token.extract_user_id(secret_key=self._secret_key)

        _LOGGER.info(f"Finding user by ID: [{user_id}]")
        authenticated_user: common_entities.AuthenticatedUser | None = (
            self._authentication_repository.find_active_user_by_id(user_id=user_id)
        )

        if not authenticated_user:
            _LOGGER.error(f"User with ID [{user_id}] not found or not active")
            raise common_exceptions.UserNotFoundException(user_id)

        _LOGGER.info(
            f"User [{authenticated_user.get_identity()}] authenticated successfully"
        )
        return common_aggregates.AuthenticationAggregate(
            user=authenticated_user, token=token
        )
