"""
Unit tests for AuthenticationToken value object.

Tests token validation and user ID extraction logic specific to AuthenticationToken.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest

from common.domain import (
    exceptions as common_exceptions,
    value_objects as common_value_objects,
)


class TestAuthenticationToken:
    """Test cases for AuthenticationToken value object."""

    def test_authentication_token_creation_with_valid_token(
        self, valid_jwt_token: str
    ) -> None:
        """Test that AuthenticationToken can be created with valid JWT."""
        # Act
        token = common_value_objects.AuthenticationToken(raw_token=valid_jwt_token)

        # Assert
        assert token.raw_token == valid_jwt_token

    def test_authentication_token_creation_with_bearer_token(
        self, valid_jwt_token: str
    ) -> None:
        """Test that AuthenticationToken can be created with Bearer token."""
        # Act
        token = common_value_objects.AuthenticationToken(
            raw_token=f"Bearer {valid_jwt_token}"
        )

        # Assert
        assert token.raw_token == valid_jwt_token

    def test_authentication_token_creation_strips_whitespace(self) -> None:
        """Test that AuthenticationToken strips whitespace from token."""
        # Arrange
        token_with_spaces = "  valid.jwt.token  "

        # Act
        token = common_value_objects.AuthenticationToken(raw_token=token_with_spaces)

        # Assert
        assert token.raw_token == "valid.jwt.token"

    def test_authentication_token_creation_with_empty_token_raises_error(self) -> None:
        """Test that empty token raises validation error."""
        # Act & Assert
        with pytest.raises(ValueError):
            common_value_objects.AuthenticationToken(raw_token="")

    def test_authentication_token_creation_with_whitespace_token_raises_error(
        self,
    ) -> None:
        """Test that whitespace-only token raises validation error."""
        # Act & Assert
        with pytest.raises(ValueError):
            common_value_objects.AuthenticationToken(raw_token="   ")

    def test_authentication_token_creation_with_null_token_raises_error(
        self,
    ) -> None:
        """Test that null token raises validation error."""
        # Act & Assert
        with pytest.raises(ValueError):
            common_value_objects.AuthenticationToken(raw_token=None)

    def test_authentication_token_immutability(self, valid_jwt_token: str) -> None:
        """Test that AuthenticationToken is immutable (inherited from BaseValueObject)."""
        # Arrange
        token = common_value_objects.AuthenticationToken(raw_token=valid_jwt_token)

        # Act & Assert
        with pytest.raises((AttributeError, ValueError)):
            token.raw_token = "modified.token"  # type: ignore[assignment]  # noqa: B010

    def test_extract_user_id_success(
        self, valid_jwt_token: str, valid_secret_key: str
    ) -> None:
        """Test successful user ID extraction from valid token."""
        # Arrange
        token = common_value_objects.AuthenticationToken(raw_token=valid_jwt_token)

        # Act
        user_id: int = token.extract_user_id(secret_key=valid_secret_key)

        # Assert
        assert isinstance(user_id, int)
        assert user_id == 123

    def test_extract_user_id_with_expired_token_raises_error(
        self, valid_secret_key: str
    ) -> None:
        """Test that expired token raises TokenExpiredException."""
        # Arrange
        expired_payload: dict[str, Any] = {
            "user_id": 123,
            "exp": datetime.now() - timedelta(hours=1),  # Expired
        }
        expired_token: str = jwt.encode(
            expired_payload, valid_secret_key, algorithm="HS256"
        )
        token = common_value_objects.AuthenticationToken(raw_token=expired_token)

        # Act & Assert
        with pytest.raises(common_exceptions.TokenExpiredException):
            token.extract_user_id(secret_key=valid_secret_key)

    def test_extract_user_id_with_invalid_signature_raises_error(
        self, valid_jwt_token: str
    ) -> None:
        """Test that invalid signature raises TokenSignatureException."""
        # Arrange
        token = common_value_objects.AuthenticationToken(raw_token=valid_jwt_token)
        wrong_secret = "wrong_secret_key"

        # Act & Assert
        with pytest.raises(common_exceptions.TokenSignatureException):
            token.extract_user_id(secret_key=wrong_secret)

    def test_extract_user_id_with_malformed_token_raises_error(
        self, valid_secret_key: str
    ) -> None:
        """Test that malformed token raises TokenDecodingException."""
        # Arrange
        malformed_token = "this.is.not.a.valid.jwt"
        token = common_value_objects.AuthenticationToken(raw_token=malformed_token)

        # Act & Assert
        with pytest.raises(common_exceptions.TokenDecodingException):
            token.extract_user_id(secret_key=valid_secret_key)

    def test_extract_user_id_with_missing_user_id_raises_error(
        self, valid_secret_key: str
    ) -> None:
        """Test that token without user_id raises TokenPayloadException."""
        # Arrange
        payload_without_user_id: dict[str, Any] = {
            "some_other_field": "value",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        }
        token_without_user_id: str = jwt.encode(
            payload_without_user_id, valid_secret_key, algorithm="HS256"
        )
        token = common_value_objects.AuthenticationToken(
            raw_token=token_without_user_id
        )

        # Act & Assert
        with pytest.raises(
            common_exceptions.authentication_exceptions.TokenPayloadException,
            match="user_id.*Token payload does not contain user_id",
        ):
            token.extract_user_id(secret_key=valid_secret_key)

    @pytest.mark.parametrize("user_id", [1, 100, 999999, 2147483647])
    def test_extract_user_id_with_various_valid_user_ids(
        self, valid_secret_key: str, user_id: int
    ) -> None:
        """Test user ID extraction with various valid user IDs."""
        # Arrange
        payload: dict[str, Any] = {
            "user_id": user_id,
            "exp": datetime.now(UTC) + timedelta(hours=1),
        }
        token_str: str = jwt.encode(payload, valid_secret_key, algorithm="HS256")
        token = common_value_objects.AuthenticationToken(raw_token=token_str)

        # Act
        extracted_user_id: int = token.extract_user_id(secret_key=valid_secret_key)

        # Assert
        assert extracted_user_id == user_id

    def test_authentication_token_equality_same_tokens(
        self, valid_jwt_token: str
    ) -> None:
        """Test that tokens with same raw token are equal."""
        # Arrange
        token1 = common_value_objects.AuthenticationToken(raw_token=valid_jwt_token)
        token2 = common_value_objects.AuthenticationToken(raw_token=valid_jwt_token)

        # Act & Assert
        assert token1 == token2

    def test_authentication_token_deserialization_validation(self) -> None:
        """Test AuthenticationToken deserialization validates data."""
        # Arrange
        invalid_data: dict[str, str] = {"raw_token": ""}  # Empty token

        # Act & Assert
        with pytest.raises(ValueError):
            common_value_objects.AuthenticationToken.from_dict(invalid_data)
