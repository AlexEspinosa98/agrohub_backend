# First, import the base repository class
from .base_repository import BaseRepository


print("Importing BaseRepository from common.domain.repositories")
# Then, import specific repositories as needed
from .authentication_repository import AuthenticationRepository
from .fake_base_repository import FakeBaseRepository
from .fake_authentication_repository import FakeAuthenticationRepository


__all__: list[str] = [
    # Base repository for all domain repositories
    "BaseRepository",
    # Authentication repository for user authentication operations
    "AuthenticationRepository",
    # Fake repository for testing purposes
    "FakeBaseRepository",
    # Fake authentication repository for testing authentication operations
    "FakeAuthenticationRepository",
]
