"""
Dependency injection composer for authentication service.

This module provides dependency injection setup for the authentication service,
ensuring proper composition of all required dependencies.
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from common.application import services as common_services
from common.config.common.settings import settings
from common.infrastructure.database.session import session_manager
from common.infrastructure.repositories import postgresql as common_pg_repos


def get_authentication_service(
    session: Session = Depends(session_manager.get_session),
) -> common_services.AuthenticationService:
    """
    Compose and return a configured authentication service.

    This function handles the dependency injection for the authentication service,
    creating all required repositories and dependencies.

    Args:
        session (Session): Database session

    Returns:
        AuthenticationService: Fully configured authentication service
    """
    auth_repository = common_pg_repos.PostgreSQLAuthenticationRepository(
        session=session
    )

    return common_services.AuthenticationService(
        authentication_repository=auth_repository,
        secret_key=settings.secret_api_key,
    )
