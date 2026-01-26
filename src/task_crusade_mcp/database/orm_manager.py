"""
ORM Manager - Centralized database connection and session management.

Provides singleton access to database connections with proper session lifecycle.
"""

import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from task_crusade_mcp.database.models.base import Base

# Thread-local storage for singleton per thread (if needed)
_thread_local = threading.local()

# Module-level singleton
_global_orm_manager: Optional["ORMManager"] = None
_global_lock = threading.Lock()


def get_default_db_path() -> str:
    """Get the default database path.

    Checks CRUSADER_DB_PATH environment variable first, then falls back
    to ~/.crusader/database.db, creating directory if needed.
    """
    # Check environment variable first
    env_db_path = os.environ.get("CRUSADER_DB_PATH")
    if env_db_path:
        # Create parent directory if needed
        db_path = Path(env_db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return str(db_path)

    # Fall back to default path
    home = Path.home()
    crusader_dir = home / ".crusader"
    crusader_dir.mkdir(parents=True, exist_ok=True)
    return str(crusader_dir / "database.db")


def get_orm_manager(db_path: Optional[str] = None) -> "ORMManager":
    """
    Get the singleton ORM manager instance.

    Args:
        db_path: Optional database path. Uses default if not provided.

    Returns:
        ORMManager singleton instance.
    """
    global _global_orm_manager

    with _global_lock:
        if _global_orm_manager is None:
            _global_orm_manager = ORMManager(db_path)
        return _global_orm_manager


def reset_orm_manager() -> None:
    """Reset the global ORM manager (for testing)."""
    global _global_orm_manager

    with _global_lock:
        if _global_orm_manager is not None:
            _global_orm_manager.close()
            _global_orm_manager = None


class ORMManager:
    """
    Centralized ORM manager for database connections.

    Manages SQLAlchemy engine and session lifecycle with proper
    connection pooling and SQLite optimizations.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the ORM manager.

        Args:
            db_path: Path to SQLite database file. Uses default if not provided.
        """
        self.db_path = db_path or get_default_db_path()
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._lock = threading.Lock()

        # Initialize engine and create tables
        self._initialize()

    def _initialize(self) -> None:
        """Initialize the database engine and create tables."""
        # Create engine with SQLite optimizations
        db_url = f"sqlite:///{self.db_path}"

        self._engine = create_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,
            connect_args={"check_same_thread": False},
        )

        # Register SQLite optimizations
        @event.listens_for(self._engine, "connect")
        def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        # Create session factory
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=True,
            expire_on_commit=False,
        )

        # Create all tables
        Base.metadata.create_all(self._engine)

    @property
    def engine(self) -> Engine:
        """Get the SQLAlchemy engine."""
        if self._engine is None:
            raise RuntimeError("ORM Manager not initialized")
        return self._engine

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a database session with automatic commit/rollback.

        Usage:
            with orm_manager.get_session() as session:
                campaign = Campaign(name="Test")
                session.add(campaign)
                # Auto-commit on successful exit
                # Auto-rollback on exception
        """
        if self._session_factory is None:
            raise RuntimeError("ORM Manager not initialized")

        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_session(self) -> Session:
        """
        Create a session without context manager.

        Caller is responsible for commit/rollback and close.
        Prefer get_session() for most use cases.
        """
        if self._session_factory is None:
            raise RuntimeError("ORM Manager not initialized")
        return self._session_factory()

    def perform_health_check(self) -> Dict[str, Any]:
        """
        Perform a database health check.

        Returns:
            Dictionary with health check results.
        """
        try:
            with self.get_session() as session:
                # Test basic query
                result = session.execute(text("SELECT 1")).scalar()
                if result != 1:
                    return {"healthy": False, "error": "Basic query failed"}

                # Check tables exist
                tables = session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                ).fetchall()
                table_names = [t[0] for t in tables]

                return {
                    "healthy": True,
                    "database_path": self.db_path,
                    "tables": table_names,
                    "table_count": len(table_names),
                }
        except Exception as e:
            return {"healthy": False, "error": str(e)}

    def close(self) -> None:
        """Close the database engine and release resources."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None

    def __del__(self) -> None:
        """Cleanup on deletion."""
        self.close()
