"""Database schema migrations (placeholder for future versions)."""

from sqlalchemy import inspect, text
from .database import get_engine


def run_migrations() -> None:
    """Run database migrations for schema upgrades."""
    engine = get_engine()
    inspector = inspect(engine)

    # Check if devices table exists
    if not inspector.has_table("devices"):
        return  # Fresh database, no migrations needed

    # Example migration: add column if missing
    with engine.connect() as conn:
        # Check for columns that might be missing from older versions
        columns = {col['name'] for col in inspector.get_columns('devices')}

        if 'os_info' not in columns:
            conn.execute(text("ALTER TABLE devices ADD COLUMN os_info TEXT"))
            conn.commit()

        if 'last_check' not in columns:
            conn.execute(text("ALTER TABLE devices ADD COLUMN last_check DATETIME"))
            conn.commit()

    # Add more migrations as schema evolves


def get_schema_version() -> int:
    """Get current schema version from settings table."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT value FROM settings WHERE key='schema_version'"))
        row = result.fetchone()
        if row:
            return int(row[0])
    return 0


def set_schema_version(version: int) -> None:
    """Set schema version in settings table."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(
            text("INSERT OR REPLACE INTO settings (key, value) VALUES ('schema_version', :v)"),
            {"v": str(version)}
        )
        conn.commit()