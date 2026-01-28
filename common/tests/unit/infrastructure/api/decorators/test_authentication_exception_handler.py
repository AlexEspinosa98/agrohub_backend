"""
Unit tests for authentication exception handler decorator.

Tests authentication-specific exception handling and HTTP response mapping.
"""

from fastapi import HTTPException
import pytest
from sqlalchemy import exc

from common.domain import exceptions as common_exceptions
from common.infrastructure.api import decorators


# Test functions decorated with handle_authentication_exceptions
@decorators.handle_authentication_exceptions
def function_normal() -> dict[str, str]:
    """Test function that returns normally."""
    return {"message": "success"}


@decorators.handle_authentication_exceptions
def function_expired_token() -> None:
    """Test function that raises TokenExpiredException."""
    raise common_exceptions.TokenExpiredException()


@decorators.handle_authentication_exceptions
def function_invalid_signature() -> None:
    """Test function that raises TokenSignatureException."""
    raise common_exceptions.TokenSignatureException()


@decorators.handle_authentication_exceptions
def function_invalid_payload() -> None:
    """Test function that raises TokenPayloadException."""
    raise common_exceptions.TokenPayloadException("user_id", "Invalid user ID format")


@decorators.handle_authentication_exceptions
def function_user_not_found() -> None:
    """Test function that raises UserNotFoundException."""
    raise common_exceptions.UserNotFoundException(123)


@decorators.handle_authentication_exceptions
def function_invalid_user_status() -> None:
    """Test function that raises InvalidUserStatusException."""
    raise common_exceptions.InvalidUserStatusException(123, "DELETED")


@decorators.handle_authentication_exceptions
def function_database_error() -> None:
    """Test function that raises SQLAlchemy error."""
    raise exc.OperationalError("Connection failed", None, None)


@decorators.handle_authentication_exceptions
def function_user_not_premium() -> None:
    """Test function that raises UserNotPremiumException."""
    raise common_exceptions.UserNotPremiumException(123)


@decorators.handle_authentication_exceptions
def function_user_not_active() -> None:
    """Test function that raises UserNotActiveException."""
    raise common_exceptions.UserNotActiveException(123, "INACTIVE")


@decorators.handle_authentication_exceptions
def function_general_auth_error() -> None:
    """Test function that raises general AuthenticationException."""
    raise common_exceptions.AuthenticationException("General auth error")


@decorators.handle_authentication_exceptions
def function_token_decoding_error() -> None:
    """Test function that raises TokenDecodingException."""
    raise common_exceptions.TokenDecodingException("Malformed token structure")


class TestAuthenticationExceptionHandler:
    """Test cases for authentication exception handler decorator."""

    def test_normal_execution(self) -> None:
        """Test normal execution without exceptions."""
        # Act
        result: dict[str, str] = function_normal()

        # Assert
        assert result == {"message": "success"}

    def test_user_not_found_exception_handling(self) -> None:
        """Test handling of UserNotFoundException."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            function_user_not_found()

        assert exc_info.value.status_code == 404
        assert (
            "Active user with ID [123] does not exist"
            in exc_info.value.detail["message"]
        )
        assert exc_info.value.detail["error_code"] == "ACTIVE_USER_NOT_FOUND"
        assert exc_info.value.detail["user_id"] == 123

    def test_invalid_user_status_exception_handling(self) -> None:
        """Test handling of InvalidUserStatusException."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            function_invalid_user_status()

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error_code"] == "INVALID_USER_STATUS"

    def test_database_operational_error_handling(self) -> None:
        """Test handling of SQLAlchemy OperationalError."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            function_database_error()

        assert exc_info.value.status_code == 503
        assert "Database temporarily unavailable" in exc_info.value.detail["message"]
        assert exc_info.value.detail["error_code"] == "DATABASE_UNAVAILABLE"

    def test_user_not_premium_exception_handling(self) -> None:
        """Test handling of UserNotPremiumException."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            function_user_not_premium()

        assert exc_info.value.status_code == 403
        assert (
            "User with ID [123] is not premium and cannot access premium features"
            in exc_info.value.detail["message"]
        )
        assert exc_info.value.detail["error_code"] == "USER_NOT_PREMIUM"

    def test_user_not_active_exception_handling(self) -> None:
        """Test handling of UserNotActiveException."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            function_user_not_active()

        assert exc_info.value.status_code == 401
        assert (
            "User with ID [123] is not active (status: [INACTIVE])"
            in exc_info.value.detail["message"]
        )
        assert exc_info.value.detail["error_code"] == "USER_NOT_ACTIVE"

    @pytest.mark.parametrize(
        "exception_class,expected_status",
        [
            (common_exceptions.TokenExpiredException, 401),
            (common_exceptions.TokenSignatureException, 401),
        ],
    )
    def test_various_token_exceptions(
        self,
        exception_class: type[common_exceptions.AuthenticationException],
        expected_status: int,
    ) -> None:
        """Test various token-related exceptions."""

        # Arrange
        @decorators.handle_authentication_exceptions
        def function_with_exception() -> None:
            raise exception_class()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            function_with_exception()

        assert exc_info.value.status_code == expected_status

    @pytest.mark.parametrize(
        "sqlalchemy_exception,expected_status",
        [
            (exc.ProgrammingError("SQL error", None, None), 500),
            (exc.IntegrityError("Constraint violation", None, None), 400),
            (exc.OperationalError("Connection error", None, None), 503),
        ],
    )
    def test_various_database_exceptions(
        self, sqlalchemy_exception: type[exc.SQLAlchemyError], expected_status: int
    ) -> None:
        """Test various SQLAlchemy exceptions."""

        # Arrange
        @decorators.handle_authentication_exceptions
        def function_with_db_exception() -> None:
            raise sqlalchemy_exception

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            function_with_db_exception()

        assert exc_info.value.status_code == expected_status

    def test_general_authentication_exception_handling(self) -> None:
        """Test handling of general AuthenticationException."""

        # Arrange
        @decorators.handle_authentication_exceptions
        def function_with_auth_exception() -> None:
            raise common_exceptions.AuthenticationException("General auth error")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            function_with_auth_exception()

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error_code"] == "AUTHENTICATION_FAILED"
        assert "General auth error" in exc_info.value.detail["message"]

    def test_token_decoding_exception_handling(self) -> None:
        """Test handling of TokenDecodingException."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            function_token_decoding_error()

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error_code"] == "TOKEN_DECODING_FAILED"
        assert (
            "Token decoding failed: [Malformed token structure]"
            in exc_info.value.detail["message"]
        )

    def test_token_payload_exception_handling(self) -> None:
        """Test handling of TokenPayloadException."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            function_invalid_payload()

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error_code"] == "INVALID_TOKEN_PAYLOAD"
        assert "user_id" in exc_info.value.detail["message"]
        assert "Invalid user ID format" in exc_info.value.detail["message"]
        assert exc_info.value.detail["field"] == "user_id"

    def test_token_expired_exception_handling(self) -> None:
        """Test handling of TokenExpiredException."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            function_expired_token()

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error_code"] == "TOKEN_EXPIRED"
        assert "Token has expired" in exc_info.value.detail["message"]

    def test_token_signature_exception_handling(self) -> None:
        """Test handling of TokenSignatureException."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            function_invalid_signature()

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error_code"] == "INVALID_TOKEN_SIGNATURE"
        assert "Invalid token signature" in exc_info.value.detail["message"]

    def test_invalid_user_status_exception_with_details(self) -> None:
        """Test handling of InvalidUserStatusException with details attribute."""

        # Arrange
        @decorators.handle_authentication_exceptions
        def function_with_details() -> None:
            exception = common_exceptions.InvalidUserStatusException(123, "DELETED")
            # Simulate adding details attribute
            exception.details = {
                "reason": "Account was deleted",
                "deleted_at": "2023-01-01",
            }
            raise exception

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            function_with_details()

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error_code"] == "INVALID_USER_STATUS"
        assert "details" in exc_info.value.detail

    def test_invalid_user_status_exception_without_details(self) -> None:
        """Test handling of InvalidUserStatusException without details attribute."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            function_invalid_user_status()

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error_code"] == "INVALID_USER_STATUS"
        assert exc_info.value.detail["details"] == {}

    @pytest.mark.parametrize(
        "exception_function,expected_error_code,expected_status",
        [
            (function_user_not_premium, "USER_NOT_PREMIUM", 403),
            (function_user_not_active, "USER_NOT_ACTIVE", 401),
            (function_expired_token, "TOKEN_EXPIRED", 401),
            (function_invalid_signature, "INVALID_TOKEN_SIGNATURE", 401),
            (function_invalid_payload, "INVALID_TOKEN_PAYLOAD", 401),
            (function_token_decoding_error, "TOKEN_DECODING_FAILED", 401),
            (function_general_auth_error, "AUTHENTICATION_FAILED", 401),
        ],
    )
    def test_authentication_exceptions_parameterized(
        self,
        exception_function: callable,
        expected_error_code: str,
        expected_status: int,
    ) -> None:
        """Test various authentication exceptions with parameterized approach."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            exception_function()

        assert exc_info.value.status_code == expected_status
        assert exc_info.value.detail["error_code"] == expected_error_code
