# First, import the base entity class
from .base_entity import BaseEntity

# Then, import specific entities as needed
from .authenticated_user import AuthenticatedUser


__all__: list[str] = [
    # Base entity for inheritance
    "BaseEntity",
    # Specific entities
    "AuthenticatedUser",
]
