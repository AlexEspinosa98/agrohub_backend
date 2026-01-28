from typing import Annotated

from fastapi import Query

from common.application.dtos import input_dto as common_input_dtos
from common.domain import enums as common_enums
from common.infrastructure.api import decorators as common_decorators


@common_decorators.handle_exceptions
def get_pagination_params(
    page: Annotated[
        int,
        Query(ge=1, description="Page number (1-based indexing)", examples=[1, 2, 10]),
    ] = 1,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description="Items per page (max 100 for performance)",
            examples=[10, 25, 50, 100],
        ),
    ] = 10,
    sort: Annotated[
        str | None,
        Query(
            description="Sort by field (e.g. 'created_at', 'updated_at')",
            examples=["created_at", "updated_at"],
        ),
    ] = None,
    sort_direction: Annotated[
        str | None,
        Query(
            description="Sort direction: 'asc' or 'desc'",
            examples=["asc", "desc"],
        ),
    ] = common_enums.SortDirection.DESC.value,
) -> common_input_dtos.PaginationInputDTO:
    """
    FastAPI dependency to extract and validate pagination parameters.

    What does it do?
    - Extracts page/limit from URL query parameters
    - Validates using FastAPI validation (not Pydantic DTO validation)
    - Returns a validated PaginationInputDTO
    - Generates automatic OpenAPI documentation

    Usage:
        @router.get("/items")
        def list_items(
            pagination: PaginationInputDTO = Depends(get_pagination_params)
        ):
            # pagination.page and pagination.limit are guaranteed valid
            pass

    Args:
        page: Page number from query parameter (?page=2)
        limit: Items per page from query parameter (?limit=25)

    Returns:
        Validated PaginationInputDTO instance

    Raises:
        HTTPException: Automatically raised by FastAPI if validation fails
    """
    return common_input_dtos.PaginationInputDTO(
        page=page,
        limit=limit,
        sort_by=sort or "created_at",
        sort_direction=sort_direction,
    )


@common_decorators.handle_exceptions
def get_optional_pagination_params(
    page: Annotated[
        int | None, Query(ge=1, description="Optional page number (1-based indexing)")
    ] = None,
    limit: Annotated[
        int | None, Query(ge=1, le=100, description="Optional items per page (max 100)")
    ] = None,
    sort: Annotated[
        str | None,
        Query(
            description="Sort by field (e.g. 'created_at', 'updated_at')",
            examples=["created_at", "updated_at"],
        ),
    ] = None,
    sort_direction: Annotated[
        str | None,
        Query(
            description="Sort direction: 'asc' or 'desc'",
            examples=["asc", "desc"],
        ),
    ] = common_enums.SortDirection.DESC.value,
) -> common_input_dtos.PaginationInputDTO | None:
    """
    FastAPI dependency for optional pagination parameters.

    What does it do?
    - Returns None if no pagination parameters provided
    - Returns validated PaginationInputDTO if parameters exist
    - Useful for endpoints that support both paginated and non-paginated responses

    Usage:
        @router.get("/items")
        def list_items(
            pagination: PaginationInputDTO | None = Depends(get_optional_pagination_params)
        ):
            if pagination:
                # Return paginated response
                return paginated_items
            else:
                # Return all items
                return all_items

    Args:
        page: Optional page number from query parameter
        limit: Optional items per page from query parameter

    Returns:
        PaginationInputDTO if parameters provided, None otherwise
    """
    if page is None and limit is None:
        return None

    return common_input_dtos.PaginationInputDTO(
        page=page or 1,
        limit=limit or 10,
        sort_by=sort or "created_at",
        sort_direction=common_enums.SortDirection(sort_direction or "desc"),
    )
