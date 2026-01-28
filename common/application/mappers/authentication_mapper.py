from common.application.dtos import output_dto as common_output_dto
from common.domain import aggregates as common_aggregates, entities as common_entities


class AuthenticationMapper:
    """
    Mapper for converting between domain objects and DTOs.

    This class handles the conversion logic, keeping DTOs as pure data structures
    and separating the mapping concerns from the domain and DTO classes.
    """

    @staticmethod
    def to_authenticated_user_dto(
        auth_result: common_aggregates.AuthenticationAggregate,
    ) -> common_output_dto.AuthenticatedUserDTO:
        """
        Convert authentication result aggregate to user DTO.

        Args:
            auth_result (AuthenticationResult): Domain authentication result

        Returns:
            AuthenticatedUserDto: DTO for API response
        """
        user: common_entities.AuthenticatedUser = auth_result.user
        return common_output_dto.AuthenticatedUserDTO(
            user_id=user.id,
            email=user.email,
            user_status=user.user_status,
            created_at=user.created_at,
            last_login=user.last_login,
            is_premium=user.is_premium,
        )
