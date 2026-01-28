"""
Unit tests for authentication service composer.

Tests dependency injection and service composition.
"""

from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from common.application import services as common_services
from common.infrastructure.services.authentication_service_composer import (
    get_authentication_service,
)


class TestAuthenticationServiceComposer:
    """Test cases for authentication service composer."""

    @pytest.fixture
    def mock_session(self) -> Mock:
        """Create mock database session."""
        return Mock(spec=Session)

    @patch("common.infrastructure.services.authentication_service_composer.settings")
    @patch(
        "common.infrastructure.services.authentication_service_composer.common_pg_repos.PostgreSQLAuthenticationRepository"
    )
    @patch(
        "common.infrastructure.services.authentication_service_composer.common_services.AuthenticationService"
    )
    def test_get_authentication_service_composition(
        self,
        mock_auth_service_class: Mock,
        mock_repository_class: Mock,
        mock_settings: Mock,
        mock_session: Mock,
    ) -> None:
        """Test that authentication service is composed correctly."""
        # Arrange
        mock_settings.secret_api_key = "test_secret_key"
        mock_repository_instance = Mock()
        mock_repository_class.return_value = mock_repository_instance
        mock_service_instance = Mock()
        mock_auth_service_class.return_value = mock_service_instance

        # Act
        result: common_services.AuthenticationService = get_authentication_service(
            session=mock_session
        )

        # Assert
        # Repository should be created with session
        mock_repository_class.assert_called_once_with(session=mock_session)

        # Service should be created with repository and secret key
        mock_auth_service_class.assert_called_once_with(
            authentication_repository=mock_repository_instance,
            secret_key="test_secret_key",
        )

        # Should return the service instance
        assert result == mock_service_instance
