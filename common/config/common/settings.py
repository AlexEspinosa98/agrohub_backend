"""
Settings configuration using pydantic-settings.
This module provides a centralized configuration for all environment variables.
"""

from enum import Enum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(Enum):
    """Environment types."""

    LOCAL = "local"
    TEST = "test"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    DEV = "dev"


class Settings(BaseSettings):
    """Global settings for the application."""

    # Environment configuration
    environment: Environment = Field(
        default=Environment.DEV,
        description="Environment (development, staging, production, dev)",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )

    # Logging configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    # CORS configuration
    cors_origins: list[str] = Field(
        default=["*"],
        description="CORS allowed origins",
    )
    cors_credentials: bool = Field(
        default=True,
        description="Allow CORS credentials",
    )
    cors_methods: list[str] = Field(
        default=["*"],
        description="CORS allowed methods",
    )
    cors_headers: list[str] = Field(
        default=["*"],
        description="CORS allowed headers",
    )

    # Database configuration
    db_user: str = Field(
        default="",
        description="Database user",
    )
    db_password: str = Field(
        default="",
        description="Database password",
    )
    db_host: str = Field(
        default="",
        description="Database host",
    )
    db_port: int = Field(
        default=5432,
        description="Database port",
    )
    db_name: str = Field(
        default="",
        description="Database name",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def postgresql_database_url(self) -> str:
        """Get the PostgreSQL database URL."""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


settings = Settings()