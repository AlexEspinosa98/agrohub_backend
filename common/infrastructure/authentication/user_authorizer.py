from fastapi import Depends, Request

from common.application.dtos import output_dto as common_output_dto
from common.application.services import authentication_service
from common.infrastructure.api import decorators as common_decorators
from common.infrastructure.services.authentication_service_composer import (
    get_authentication_service,
)


def get_user_from_token(
    request: Request,
    authentication_service: authentication_service.AuthenticationService = Depends(
        get_authentication_service
    ),
) -> common_output_dto.AuthenticatedUserDTO:
    """
    Clean authentication function without HTTP exception handling.

    The @handle_authentication_exceptions decorator handles all domain exceptions
    and converts them to appropriate HTTP responses.
    """
    raw_token: str = _extract_token_from_request(request=request)

    return authentication_service.authenticate_user_from_token(raw_token=raw_token)


def get_user_from_token_optional(
    request: Request,
    authentication_service: authentication_service.AuthenticationService = Depends(
        get_authentication_service
    ),
) -> common_output_dto.AuthenticatedUserDTO | None:
    """
    Optional authentication without decorator since we want to return None.
    """
    raw_token: str = _extract_token_from_request(request=request)

    return authentication_service.authenticate_user_from_token_optional(
        raw_token=raw_token
    )


def _extract_token_from_request(request: Request) -> str:
    """Extract token from request headers."""
    return request.headers.get("Authorization", "")


@common_decorators.handle_authentication_exceptions
def get_current_user(
    request: Request,
    auth_service: authentication_service.AuthenticationService = Depends(
        get_authentication_service
    ),
) -> common_output_dto.AuthenticatedUserDTO:
    """
    Convenience function for getting current authenticated user.

    This is the main function that FastAPI routes should use for authentication.

    Args:
        request (Request): HTTP request
        auth_service (AuthenticationService): Authentication service

    Returns:
        AuthenticatedUserDto: Current authenticated user
    """
    return get_user_from_token(request=request, authentication_service=auth_service)


def get_current_user_optional(
    request: Request,
    auth_service: authentication_service.AuthenticationService = Depends(
        get_authentication_service
    ),
) -> common_output_dto.AuthenticatedUserDTO | None:
    """
    Convenience function for getting current authenticated user, returning None if not authenticated.

    This is the main function that FastAPI routes should use for optional authentication.

    Args:
        request (Request): HTTP request
        auth_service (AuthenticationService): Authentication service

    Returns:
        AuthenticatedUserDto | None: Current authenticated user or None if not authenticated
    """
    return get_user_from_token_optional(
        request=request, authentication_service=auth_service
    )
