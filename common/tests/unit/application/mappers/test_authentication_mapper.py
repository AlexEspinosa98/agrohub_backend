"""
Unit tests for AuthenticationMapper.

Tests mapping logic between domain objects and DTOs.
"""

from datetime import datetime

import pytest

from common.application.dtos import output_dto as common_output_dto
from common.application.mappers.authentication_mapper import AuthenticationMapper
from common.domain import (
    aggregates as common_aggregates,
    entities as common_entities,
    enums as common_enums,
    value_objects as common_value_objects,
)
from common.tests.unit.domain.entities import builders as common_entity_builders


class TestAuthenticationMapper:
    """Test cases for AuthenticationMapper."""

    @pytest.fixture
    def sample_authentication_aggregate(
        self,
    ) -> common_aggregates.AuthenticationAggregate:
        """Create a sample authentication aggregate for testing."""
        user: common_entities.AuthenticatedUser = (
            common_entity_builders.AuthenticatedUserBuilder()
            .with_id(123)
            .with_email("test@example.com")
            .with_status(common_enums.UserStatus.ACTIVE)
            .with_created_at(datetime(2023, 1, 1, 12, 0, 0))
            .with_updated_at(datetime(2023, 1, 2, 12, 0, 0))
            .with_last_login(datetime(2023, 1, 3, 12, 0, 0))
            .build()
        )

        token = common_value_objects.AuthenticationToken(raw_token="valid.jwt.token")

        return common_aggregates.AuthenticationAggregate(user=user, token=token)

    def test_to_authenticated_user_dto_conversion(
        self, sample_authentication_aggregate: common_aggregates.AuthenticationAggregate
    ) -> None:
        """Test conversion from authentication aggregate to DTO."""
        # Act
        dto: common_output_dto.AuthenticatedUserDTO = (
            AuthenticationMapper.to_authenticated_user_dto(
                sample_authentication_aggregate
            )
        )

        # Assert
        assert isinstance(dto, common_output_dto.AuthenticatedUserDTO)
        user: common_entities.AuthenticatedUser = sample_authentication_aggregate.user

        assert dto.user_id == 123 == user.id
        assert dto.email == "test@example.com" == user.email
        assert dto.user_status == common_enums.UserStatus.ACTIVE
        assert dto.created_at == datetime(2023, 1, 1, 12, 0, 0) == user.created_at
        assert dto.last_login == datetime(2023, 1, 3, 12, 0, 0) == user.last_login

    def test_to_authenticated_user_dto_with_null_last_login(self) -> None:
        """Test conversion when user has no last login."""
        # Arrange
        user: common_entities.AuthenticatedUser = (
            common_entity_builders.AuthenticatedUserBuilder()
            .with_id(456)
            .with_email("noLogin@example.com")
            .with_status(common_enums.UserStatus.ACTIVE)
            .with_created_at(datetime(2023, 1, 1, 12, 0, 0))
            .with_updated_at(datetime(2023, 1, 2, 12, 0, 0))
            .with_last_login(None)  # No last login
            .build()
        )

        token = common_value_objects.AuthenticationToken(raw_token="valid.jwt.token")
        aggregate = common_aggregates.AuthenticationAggregate(user=user, token=token)

        # Act
        dto: common_output_dto.AuthenticatedUserDTO = (
            AuthenticationMapper.to_authenticated_user_dto(aggregate)
        )

        # Assert
        assert dto.user_id == 456
        assert dto.email == "noLogin@example.com"
        assert dto.last_login is None
