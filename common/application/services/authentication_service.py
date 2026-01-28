from common.application import mappers as common_mappers
from common.application.dtos import output_dto as common_output_dto
from common.application.use_cases.authenticate_user import (
    AuthenticateUserUseCase,
)
from common.domain import (
    aggregates as common_aggregates,
    repositories as common_repositories,
)


class AuthenticationService:
    """
    Application service for authentication operations.

    Orchestrates authentication use cases and coordinates domain operations.
    This is the main entry point for authentication from the infrastructure layer.
    """

    def __init__(
        self,
        authentication_repository: common_repositories.AuthenticationRepository,
        secret_key: str,
    ) -> None:
        """
        Initialize the authentication service.

        Args:
            authentication_repository (AuthenticationRepository): Repository for authentication data access
            secret_key (str): JWT secret key for token validation
        """
        self._authentication_repository: common_repositories.AuthenticationRepository = authentication_repository
        self._secret_key: str = secret_key
        self._authenticate_user_use_case = AuthenticateUserUseCase(
            authentication_repository, secret_key
        )
        self._mapper = common_mappers.AuthenticationMapper()

    def authenticate_user_from_token(
        self, raw_token: str
    ) -> common_output_dto.AuthenticatedUserDTO:
        """
        Authenticate a user from a JWT token and return user information.
        This is the main method that infrastructure will call to authenticate users.

        Args:
            raw_token (str): Raw JWT token from request headers

        Returns:
            AuthenticatedUserDto: Authenticated user information

        Raises:
            AuthenticationException: If authentication fails for any reason
        """
        auth_result: common_aggregates.AuthenticationAggregate = (
            self._authenticate_user_use_case.execute(raw_token=raw_token)
        )

        return self._mapper.to_authenticated_user_dto(auth_result)

    def authenticate_user_from_token_optional(
        self, raw_token: str | None = None
    ) -> common_output_dto.AuthenticatedUserDTO | None:
        """
        Optional authentication - returns None if token is not provided or invalid.

        Useful for endpoints that support both authenticated and anonymous access.

        Args:
            raw_token (Optional[str]): Raw JWT token from request headers

        Returns:
            Optional[AuthenticatedUserDto]: User info if valid token, None otherwise
        """
        if not raw_token:
            return None

        return self.authenticate_user_from_token(raw_token=raw_token)
