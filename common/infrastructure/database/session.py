"""
SQLAlchemy session manager implementation with improved singleton pattern.
"""

import threading
from typing import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from common.config.common.settings import settings


class SQLAlchemySessionManager:
    """
    SQLAlchemy implementation of the session manager with thread-safe singleton pattern.

    This class manages database connections and provides sessions for database operations.
    Uses the singleton pattern to ensure only one instance manages the connection pool.
    """

    _instance = None
    _lock = threading.Lock()
    _initialized: bool

    def __new__(cls) -> "SQLAlchemySessionManager":
        """
        Thread-safe singleton implementation.

        Returns:
            SQLAlchemySessionManager: The singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """
        Initialize the session manager (only once due to singleton pattern).
        """
        if hasattr(self, "_initialized") and self._initialized:
            return

        with self._lock:
            if hasattr(self, "_initialized") and self._initialized:
                return

            self._initialize_engine()
            self._initialized = True

    def _initialize_engine(self) -> None:
        """
        Initialize the SQLAlchemy engine and session factory.
        """
        self.engine: Engine = create_engine(
            settings.postgresql_database_url,
            # Connection pool settings
            pool_pre_ping=True,  # Verify connections before use
            pool_size=10,  # Number of connections to maintain
            max_overflow=20,  # Additional connections allowed
            pool_timeout=30,  # Timeout waiting for connection
            pool_recycle=3600,  # Recycle connections after 1 hour
            # Performance settings
            echo=settings.debug,  # Log SQL queries in debug mode
            # Connection arguments
            connect_args={
                "connect_timeout": 10,
                "application_name": "sona-application",
            },
        )

        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            expire_on_commit=False,  # Keep objects accessible after commit
        )

    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a database session with proper error handling and cleanup.

        Yields:
            Session: Database session that will be automatically closed

        Example:
            ```python
            async def my_endpoint(session: Session = Depends(session_manager.get_session)):
                # Use session here
                pass
            ```
        """
        session: Session = self.SessionLocal()
        try:
            yield session
            # Commit any pending transactions
            session.commit()
        except Exception:
            # Rollback on any exception
            session.rollback()
            raise
        finally:
            # Always close the session
            session.close()

    def close_all_connections(self) -> None:
        """
        Close all database connections.

        Useful for graceful shutdown or testing cleanup.
        """
        if hasattr(self, "engine"):
            self.engine.dispose()

    def get_engine(self) -> Engine:
        """
        Get the SQLAlchemy engine.

        Returns:
            Engine: The SQLAlchemy engine instance
        """
        return self.engine

    def create_all_tables(self) -> None:
        """
        Create all tables defined in the models.

        Note: In production, use Alembic migrations instead.
        This is mainly for testing or initial setup.
        """
        from common.infrastructure.database.models.base import BaseModel

        BaseModel.metadata.create_all(bind=self.engine)

    def drop_all_tables(self) -> None:
        """
        Drop all tables.

        Warning: This will delete all data! Use only for testing.
        """
        from common.infrastructure.database.models.base import BaseModel

        BaseModel.metadata.drop_all(bind=self.engine)

    def __repr__(self) -> str:
        """String representation of the session manager."""
        return f"SQLAlchemySessionManager(engine={self.engine.url if hasattr(self, 'engine') else 'Not initialized'})"


# Create a singleton instance
session_manager = SQLAlchemySessionManager()
