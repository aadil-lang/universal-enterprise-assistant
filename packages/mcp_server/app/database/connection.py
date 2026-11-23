"""
Database connection management for Acme Corporation MCP Server.
Provides pooled, parameterized, read-only database connections using SQLAlchemy and Psycopg2.
Supports dependency injection for test environments.
"""

import logging
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import Connection, create_engine
from sqlalchemy.exc import SQLAlchemyError

from app.config.settings import get_mcp_settings

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Sanitized database exception that avoids exposing internal credentials or raw SQL."""
    pass


class DatabaseManager:
    """Manages SQLAlchemy connection pooling and lifecycle for MCP tools."""

    def __init__(self, database_url: Optional[str] = None):
        self.settings = get_mcp_settings()
        self.database_url = database_url or self.settings.DATABASE_URL
        self._engine = None

    @property
    def engine(self):
        """Lazily creates and returns the SQLAlchemy engine."""
        if self._engine is None:
            connect_args = {}
            if self.database_url.startswith("sqlite"):
                connect_args["check_same_thread"] = False

            self._engine = create_engine(
                self.database_url,
                pool_pre_ping=True,
                future=True,
                connect_args=connect_args,
            )
        return self._engine

    @engine.setter
    def engine(self, value):
        """Allows assigning a custom engine (for testing)."""
        self._engine = value

    @contextmanager
    def get_connection(self) -> Generator[Connection, None, None]:
        """
        Context manager providing an active database connection.
        Ensures the connection is always safely returned to the pool or closed.
        """
        try:
            conn = self.engine.connect()
        except Exception as conn_err:
            logger.error("Failed to acquire database connection: %s", conn_err)
            raise DatabaseError("Database service is currently unreachable.") from conn_err

        try:
            yield conn
        except SQLAlchemyError as sql_err:
            logger.error("Database query execution error: %s", sql_err)
            raise DatabaseError("Database operation failed.") from sql_err
        except Exception as exc:
            logger.error("Unexpected database error: %s", exc)
            raise DatabaseError("Unexpected error during database operation.") from exc
        finally:
            conn.close()

    def dispose(self):
        """Disposes the engine connection pool."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None


# Module-level singleton instance with test override support
_db_manager_instance: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Returns the active DatabaseManager instance."""
    global _db_manager_instance
    if _db_manager_instance is None:
        _db_manager_instance = DatabaseManager()
    return _db_manager_instance


def set_db_manager(manager: Optional[DatabaseManager]) -> None:
    """Sets a custom DatabaseManager instance (primarily for testing with in-memory SQLite)."""
    global _db_manager_instance
    _db_manager_instance = manager
