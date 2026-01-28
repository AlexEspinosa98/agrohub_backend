# Common Package Documentation

The common package contains common functionality, infrastructure components, and utilities that are used across all modules in the Sona application. This package follows Domain-Driven Design (DDD) and Hexagonal Architecture principles.

## 🏗️ Architecture

The common package is organized into three main layers:

### Domain Layer

Contains core business abstractions and interfaces that are domain-agnostic:

```
domain/
├── entities/              # Base entity abstractions
│   └── base_entity.py    # Common entity interface
├── repositories/          # Repository interfaces and base implementations
│   ├── base_repository.py        # Repository interface
│   └── fake_base_repository.py   # In-memory implementation for testing
└── exceptions/           # Domain exceptions
    └── base_exceptions.py # Common exception types
```

### Application Layer

Contains application-level services and DTOs that can be shared:

```
application/
├── dtos/                 # Common Data Transfer Objects
│   └── base_dto.py      # Base DTO with common functionality
├── services/            # Application services
│   └── authentication_service.py  # Authentication business logic
├── use_cases/           # Domain use cases
│   └── authenticate_user.py      # User authentication use case
└── mappers/             # Entity to DTO mapping
    └── authentication_mapper.py  # Authentication mapping logic
```

### Infrastructure Layer

Contains technical implementations and configurations:

```
infrastructure/
├── database/             # Database configuration and models
│   ├── session.py       # Database session management
│   ├── models/          # SQLAlchemy models
│   │   ├── base.py     # Base model class
│   │   └── user.py     # User model
│   └── repositories/    # Base repository implementations
│       └── postgresql/  # PostgreSQL specific implementations
├── api/                 # API infrastructure
│   ├── middleware/      # FastAPI middleware
│   ├── decorators/      # API decorators (error handling, etc.)
│   └── auth/           # Authentication infrastructure
│       └── user_authorizer.py  # FastAPI authentication
├── logging/             # Logging configuration
│   └── config.py       # Centralized logging setup
└── services/           # Infrastructure service orchestration
    └── authentication_service_orchestrator.py  # DI container
```

## 🔧 Core Components

### Authentication System

Complete authentication system with DDD principles:

#### Value Objects

```python
# Authentication Token - encapsulates JWT logic
class AuthenticationToken(BaseValueObject):
    raw_token: str

    def extract_user_id(self, secret_key: str) -> UserId:
        """Extract and validate user ID from token."""
        pass

# User ID - ensures valid user identifiers
class UserId(BaseValueObject):
    value: int  # Always positive integer
```

#### Entities

```python
# Authenticated User - minimal user for auth context
class AuthenticatedUser(BaseEntity):
    user_id: UserId
    email: str
    user_status: UserStatus
    last_login: Optional[datetime]

    def is_active(self) -> bool:
        """Check if user can authenticate."""
        pass
```

#### Aggregates

```python
# Authentication Result - consistency boundary
class AuthenticationAggregate(BaseAggregate):
    user: AuthenticatedUser
    token: AuthenticationToken

    def validate_invariants(self) -> None:
        """Ensure user and token are consistent."""
        pass
```

#### Use Cases

```python
# Authentication Use Case - pure business logic
class AuthenticateUserUseCase:
    def execute(self, raw_token: str) -> AuthenticationAggregate:
        """Authenticate user with comprehensive validation."""
        pass
```

### Comprehensive Logging

**Security-focused logging throughout the authentication flow:**

#### Repository Level

```
INFO - Authentication attempt - searching for user_id: 123
INFO - Authentication successful - user found: user@example.com (id: 123, status: ACTIVE)
WARNING - Authentication failed - user_id 999 not found or inactive
```

#### Use Case Level

```
INFO - Starting user authentication process
INFO - Token decoded successfully - user_id: 123
INFO - Authentication completed successfully for user 123 (user@example.com)
```

#### Service Level

```
INFO - AuthenticationService.authenticate_user_from_token called
INFO - Authentication service completed successfully - user_id: 123, email: user@example.com
```

#### Infrastructure Level

```
INFO - Authentication attempt from IP: 192.168.1.100, User-Agent: Mozilla/5.0...
INFO - Authentication successful - user_id: 123, email: user@example.com, IP: 192.168.1.100
WARNING - Authentication failed - Status: 401, Detail: Token expired, IP: 192.168.1.100
```

### Exception Handling

**Domain-specific exceptions with HTTP mapping:**

```python
# Domain exceptions
class AuthenticationException(DomainException):
    """Base authentication exception."""

class TokenExpiredException(AuthenticationException):
    """Token has expired."""

class ActiveUserNotFoundException(AuthenticationException):
    """User not found or inactive."""

# Automatic HTTP mapping
@handle_auth_exceptions
def endpoint():
    # TokenExpiredException -> 401 HTTP response
    # ActiveUserNotFoundException -> 404 HTTP response
    pass
```

### Base Entity

All domain entities inherit from `BaseEntity`:

```python
class BaseEntity:
    """Base class for all domain entities."""
    id: Optional[int] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
```

**Features**:

-   Common fields for all entities
-   Soft delete support
-   Timestamp tracking
-   Dictionary conversion methods

### Base Repository

Repository interface that all repositories must implement:

```python
class BaseRepository(ABC, Generic[T]):
    """Abstract base repository interface."""

    @abstractmethod
    def save(self, entity: T) -> T:
        """Save an entity."""
        pass

    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[T]:
        """Get entity by ID."""
        pass

    @abstractmethod
    def list_all(self) -> list[T]:
        """List all entities."""
        pass

    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """Delete entity by ID."""
        pass
```

**Benefits**:

-   Consistent interface across all repositories
-   Easy to mock for testing
-   Type-safe with generics
-   Supports dependency inversion

## 🧪 Testing Infrastructure

### Test Configuration

The common package provides global test configuration in `conftest.py`:

```python
@pytest.fixture(name="session")
def session_fixture():
    """Create SQLite in-memory database session for tests."""
    # Creates fresh database for each test
    # Automatically creates all tables
    # Provides clean session
```

### Authentication Testing

```python
# Unit test with fake repository
def test_authentication_with_fake_repo():
    fake_repo = FakeAuthenticationRepository()
    use_case = AuthenticateUserUseCase(fake_repo, "secret")

    # Test successful authentication
    result = use_case.execute("valid_token")
    assert result.user.user_id.value == 123

# Integration test with real database
def test_authentication_with_real_db(session):
    repo = PostgreSQLAuthenticationRepository(session)
    # Create test user in database
    # Test authentication flow
```

## 📚 Usage Examples

### Using Authentication in FastAPI

```python
from common.infrastructure.api.auth.user_authorizer import get_current_user
from common.application.dtos.authentication_dto import AuthenticatedUserDto

@router.get("/protected")
def protected_endpoint(
    current_user: AuthenticatedUserDto = Depends(get_current_user)
):
    """Endpoint requiring authentication."""
    return {"user_id": current_user.user_id, "email": current_user.email}

@router.get("/optional-auth")
def optional_auth_endpoint(
    current_user: Optional[AuthenticatedUserDto] = Depends(get_user_from_token_optional)
):
    """Endpoint with optional authentication."""
    if current_user:
        return {"message": f"Hello {current_user.email}"}
    return {"message": "Hello anonymous user"}
```

### Custom Authentication Logic

```python
from common.application.services.authentication_service import AuthenticationService

# In your module
def custom_auth_logic(auth_service: AuthenticationService, token: str):
    try:
        user = auth_service.authenticate_user_from_token(token)
        # Custom business logic
        return user
    except AuthenticationException as e:
        # Handle authentication failure
        logger.warning(f"Auth failed: {e}")
        return None
```

## 🔧 Configuration

### Authentication Configuration

```python
# JWT settings
JWT_SECRET_KEY = "your-secret-key"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Database settings
DATABASE_URL = "postgresql://user:pass@localhost/db"
```

### Logging Configuration

```python
# Logging settings for authentication
AUTH_LOG_LEVEL = "INFO"  # Set to DEBUG for detailed token info
SECURITY_LOG_LEVEL = "WARNING"  # For failed auth attempts
```

## 🚀 Development Guidelines

### Adding Authentication to New Modules

1. **Import the authorizer**:

    ```python
    from common.infrastructure.api.auth.user_authorizer import get_current_user
    ```

2. **Use dependency injection**:

    ```python
    def endpoint(user: AuthenticatedUserDto = Depends(get_current_user)):
        pass
    ```

3. **Handle optional authentication**:
    ```python
    from common.infrastructure.api.auth.user_authorizer import get_user_from_token_optional
    ```

### Security Best Practices

1. **Always log authentication attempts**
2. **Use specific exceptions for different failure types**
3. **Validate user permissions at the business logic level**
4. **Monitor failed authentication attempts**
5. **Use rate limiting for authentication endpoints**

### Testing Authentication

```python
# Create test tokens
def create_test_token(user_id: int, secret: str) -> str:
    payload = {"user_id": user_id, "exp": datetime.utcnow() + timedelta(hours=1)}
    return jwt.encode(payload, secret, algorithm="HS256")

# Test with invalid tokens
def test_expired_token():
    expired_token = create_expired_token()
    with pytest.raises(TokenExpiredException):
        use_case.execute(expired_token)
```

## 🔢 Pagination System

Complete pagination system with comprehensive features and best practices:

### Core Components

#### DTOs and Value Objects

```python
# Pagination Input - Request validation
class PaginationInputDTO(BaseDTO):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, ge=1, le=100)

    def calculate_offset(self) -> int:
        return (self.page - 1) * self.limit

# Essential Metadata
class PaginationMetadataDTO(BaseDTO):
    current_page: int
    total_pages: int
    total_items: int
    has_next: bool
    has_previous: bool
```

#### FastAPI Dependencies

```python
from common.infrastructure.api.dependencies.pagination_dependencies import (
    get_pagination_params,
    get_optional_pagination_params,
)

@router.get("/items")
def list_items(
    pagination: PaginationInputDTO = Depends(get_pagination_params),
):
    # pagination.page and pagination.limit are automatically validated
    pass
```

#### API Response Wrappers

```python
# Generic paginated response
class PaginatedResponseDTO(BaseDTO, Generic[TDataItem]):
    items: list[TDataItem]
    pagination: PaginationMetadataDTO

# API wrapper with success/error structure
class PaginatedApiResponseDTO(ApiResponseDTO[PaginatedResponseDTO[TResponseData]]):
    @classmethod
    def create_paginated_success(cls, items, pagination_input, total_items):
        # Factory method for consistent responses
```

### Usage Examples

#### Basic Paginated Endpoint

```python
from common.infrastructure.api.dependencies.pagination_dependencies import get_pagination_params
from common.infrastructure.api.dtos.pagination_response_dto import PaginatedApiResponseDTO

@router.get("/favorite-media")
def list_favorite_media(
    pagination: PaginationInputDTO = Depends(get_pagination_params),
) -> PaginatedApiResponseDTO[FavoriteMediaDTO]:

    # Get data from repository with pagination
    items, total = media_service.get_favorites_paginated(
        page=pagination.page,
        limit=pagination.limit
    )

    # Return paginated response
    return PaginatedApiResponseDTO.create_paginated_success(
        items=items,
        pagination_input=pagination,
        total_items=total,
        message="Favorite media retrieved successfully"
    )
```

#### Repository Pattern for Pagination

```python
# In your repository
def find_items_paginated(
    self,
    page: int,
    limit: int
) -> tuple[list[Entity], int]:
    offset = (page - 1) * limit
    items = self.query().offset(offset).limit(limit).all()
    total = self.query().count()
    return items, total

# In your use case
def execute(self, pagination_input: PaginationInputDTO):
    items, total = self.repository.find_items_paginated(
        pagination_input.page,
        pagination_input.limit
    )

    return PaginatedResponseDTO.create_response(
        items=items,
        pagination_input=pagination_input,
        total_items=total,
    )
```

### Response Structure

```json
{
    "success": true,
    "message": "Data retrieved successfully",
    "data": {
        "items": [
            {
                "id": 123,
                "name": "Item 1"
            }
        ],
        "pagination": {
            "current_page": 2,
            "total_pages": 5,
            "total_items": 47,
            "has_next": true,
            "has_previous": true
        }
    }
}
```

### Features

**✅ Simple Validation:**

-   Page must be ≥ 1
-   Limit between 1-100 for performance
-   Clear error messages with Pydantic

**✅ Essential Metadata:**

-   Navigation info (has_next, has_previous)
-   Basic counts (current_page, total_pages, total_items)
-   Clean and minimal structure

**✅ Type Safety:**

-   Generic types for compile-time safety
-   TypeVar for data items and responses
-   Full mypy compatibility

**✅ FastAPI Integration:**

-   Automatic parameter extraction
-   Built-in validation
-   OpenAPI documentation generation

**✅ Developer Experience:**

-   Factory methods for easy creation
-   Consistent API across all endpoints
-   Simple and predictable structure

## 📦 Dependencies

### Core Dependencies

-   **SQLAlchemy**: ORM and database abstraction
-   **Pydantic**: Data validation and serialization
-   **FastAPI**: Web framework components
-   **PyJWT**: JWT token handling
-   **pytest**: Testing framework

### Development Dependencies

-   **ruff**: Linting and formatting
-   **mypy**: Type checking
-   **pytest-cov**: Test coverage

## 🔄 Migration Status

### ✅ Completed Components

-   Complete authentication system with DDD
-   Comprehensive logging throughout all layers
-   Exception handling with HTTP mapping
-   Value objects for secure token handling
-   Repository pattern with PostgreSQL implementation
-   Testing infrastructure
-   FastAPI integration

### 🔄 In Progress

-   Performance monitoring for authentication
-   Rate limiting integration
-   Advanced audit logging

### 📋 Planned Features

-   Multi-factor authentication support
-   OAuth provider integration
-   Session management
-   Advanced security monitoring

## 🤝 Contributing

When contributing to the common package:

1. **Follow DDD principles**: Keep domain logic pure and separate from infrastructure
2. **Add comprehensive logging**: Especially for security-related operations
3. **Maintain backwards compatibility**: Changes affect all modules
4. **Add tests**: Both unit and integration tests for new features
5. **Document security implications**: Authentication changes require security review

## 📞 Support

For questions about authentication or the common package:

-   Check authentication examples in the code
-   Review test cases for usage patterns
-   Check logs for detailed authentication flow information
-   Create issue with authentication-specific details

---

**Note**: The common package is the foundation of the entire application. Authentication changes should be carefully considered and thoroughly tested as they impact security across all modules.
