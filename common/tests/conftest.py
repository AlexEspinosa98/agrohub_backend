"""
Common tests conftest.
Provides fixtures specific to common module testing.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest

from common.domain import (
    entities as common_entities,
    enums as common_enums,
)


@pytest.fixture
def sample_authenticated_user() -> common_entities.AuthenticatedUser:
    """Create a sample authenticated user for testing."""
    return common_entities.AuthenticatedUser(
        email="test@example.com",
        user_status=common_enums.UserStatus.ACTIVE,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        last_login=None,
        id=123,
    )


@pytest.fixture
def valid_secret_key() -> str:
    """Valid secret key for JWT operations."""
    return "test_secret_key_123"


@pytest.fixture
def valid_token_payload() -> dict:
    """Valid token payload."""
    return {"user_id": 123, "exp": datetime.now(UTC) + timedelta(hours=1)}


@pytest.fixture
def valid_jwt_token(valid_token_payload: dict[str, Any], valid_secret_key: str) -> str:
    """Create a valid JWT token."""
    return jwt.encode(valid_token_payload, valid_secret_key, algorithm="HS256")
