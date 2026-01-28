# First, import the base aggregate class
from .base_aggregate import BaseAggregate

# Then, import specific aggregates as needed
from .authentication_result import AuthenticationAggregate


__all__: list[str] = [
    # Base aggregate for inheritance
    "BaseAggregate",
    # Authentication-related aggregate
    "AuthenticationAggregate",
]
