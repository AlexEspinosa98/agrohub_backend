class AuthenticationException(Exception):
    """Base exception for authentication-related errors."""


class InvalidTokenException(AuthenticationException):
    """Raised when a JWT token is invalid."""

    def __init__(self, message: str = "Invalid authentication token") -> None:
        super().__init__(message)


class UserNotFoundException(AuthenticationException):
    """Raised when an authenticated user is not found in the system."""

    def __init__(self, user_id: int) -> None:
        super().__init__(f"User with ID [{user_id}] does not exist")
        self.user_id: int = user_id


class TokenExpiredException(InvalidTokenException):
    """Raised when JWT token has expired."""

    def __init__(self) -> None:
        super().__init__("Token has expired")


class TokenSignatureException(InvalidTokenException):
    """Raised when JWT token signature is invalid."""

    def __init__(self) -> None:
        super().__init__("Invalid token signature, token may have been tampered with")


class TokenDecodingException(InvalidTokenException):
    """Raised when JWT token cannot be decoded."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"Cannot decode token: [{reason}]")
        self.reason: str = reason


class TokenPayloadException(InvalidTokenException):
    """Raised when JWT token payload is invalid."""

    def __init__(self, field: str, reason: str) -> None:
        super().__init__(f"Invalid token payload - [{field}]: [{reason}]")
        self.field: str = field
        self.reason: str = reason


class InvalidUserStatusException(AuthenticationException):
    """Raised when trying to authenticate a user with an invalid status (e.g., inactive, blocked, pending, etc.)."""

    def __init__(self, user_id: int, status: str) -> None:
        super().__init__(
            f"Cannot authenticate user with ID [{user_id}], invalid status [{status}]"
        )
        self.user_id: int = user_id
        self.status: str = status


class UserNotActiveException(AuthenticationException):
    """Raised when user is not active."""

    def __init__(self, user_id: int, status: str) -> None:
        self.user_id = user_id
        self.status = status
        super().__init__(f"User with ID [{user_id}] is not active (status: [{status}])")


class UserNotPremiumException(AuthenticationException):
    """Raised when user is not premium."""

    def __init__(self, user_id: int) -> None:
        self.user_id = user_id
        super().__init__(
            f"User with ID [{user_id}] is not premium and cannot access premium features"
        )
