"""Database session and initialization."""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine import Engine

from .models import Base
from ..config import get_config


_engine: Engine | None = None
_session_factory: sessionmaker | None = None


def get_engine() -> Engine:
    """Get or create the SQLAlchemy engine."""
    global _engine
    if _engine is None:
        db_path = get_config().get("app.database_path", "netops_commander.db")
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,
            future=True,
            connect_args={"check_same_thread": False},
        )
        # Enable foreign keys for SQLite
        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return _engine


def get_session_factory() -> sessionmaker:
    """Get or create the session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            class_=Session,
            expire_on_commit=False,
        )
    return _session_factory


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database() -> None:
    """Initialize database - create all tables and run lightweight migrations."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    # Import here to avoid circular import at module load
    from .migrations import run_migrations

    run_migrations()


def drop_database() -> None:
    """Drop all tables (use with caution)."""
    engine = get_engine()
    Base.metadata.drop_all(engine)


def get_session() -> Session:
    """Get a new session (caller must close)."""
    return get_session_factory()()


def vacuum_database() -> None:
    """Vacuum the SQLite database to reclaim space (SQLAlchemy 2.x safe)."""
    from sqlalchemy import text

    engine = get_engine()
    # VACUUM cannot run inside a transaction on SQLite
    with engine.connect() as conn:
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        conn.execute(text("VACUUM"))


def reset_engine() -> None:
    """Dispose and clear the global engine (for tests / config path changes)."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None