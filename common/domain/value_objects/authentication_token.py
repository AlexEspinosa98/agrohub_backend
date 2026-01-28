from typing import Any

import jwt
from pydantic import Field, ValidationError, field_validator

from common.domain import value_objects as common_value_objects
from common.domain.exceptions import authentication_exceptions


class AuthenticationToken(common_value_objects.BaseValueObject):
    """
    Value object representing a JWT authentication token.

    Encapsulates token validation and extraction logic following DDD principles.
    This ensures tokens are always valid when created.
    """

    raw_token: str = Field(min_length=1, description="JWT token string")

    @field_validator("raw_token")
    @classmethod
    def validate_and_clean_token(cls, token_value: str) -> str:
        """Validate and clean token format on creation."""
        return cls._clean_token_static(token=token_value)

    @staticmethod
    def _clean_token_static(token: str) -> str:
        """Remove Bearer prefix if present."""
        token = token.strip()
        if token.startswith("Bearer "):
            return token[7:].strip()
        return token

    def extract_user_id(self, secret_key: str) -> int:
        """
        Extract user ID from token payload.

        Args:
            secret_key (str): Secret key for JWT decoding

        Returns:
            int: User ID from token

        Raises:
            TokenPayloadException: If token payload is invalid
        """
        try:
            payload: dict[str, Any] = self.decode(secret_key=secret_key)

            return payload["user_id"]

        except ValueError as e:
            raise authentication_exceptions.TokenPayloadException("user_id", str(e))
        except ValidationError as e:
            raise authentication_exceptions.TokenPayloadException(
                "user_id", f"Invalid token payload: [{str(e)}]"
            )
        except KeyError:
            raise authentication_exceptions.TokenPayloadException(
                "user_id", "Token payload does not contain user_id"
            )

    def decode(self, secret_key: str) -> dict[str, Any]:
        """
        Decode the JWT token using the provided secret key.

        Args:
            secret_key (str): Secret key for JWT decoding

        Returns:
            dict: Decoded token payload

        Raises:
            TokenExpiredException: If token has expired
            TokenSignatureException: If token signature is invalid
            TokenDecodingException: If token cannot be decoded
        """
        if not secret_key:
            raise authentication_exceptions.TokenDecodingException(
                "Secret key cannot be empty"
            )

        try:
            return jwt.decode(jwt=self.raw_token, key=secret_key, algorithms=["HS256"])

        except jwt.ExpiredSignatureError:
            raise authentication_exceptions.TokenExpiredException()
        except jwt.InvalidSignatureError:
            raise authentication_exceptions.TokenSignatureException()
        except jwt.DecodeError:
            raise authentication_exceptions.TokenDecodingException(
                "Token format is invalid or corrupted"
            )
        except jwt.InvalidTokenError as e:
            raise authentication_exceptions.TokenDecodingException(
                f"Token validation failed: [{str(e)}]"
            )
