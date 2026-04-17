"""
SQLAlchemy database engine and session management.
Connects to Supabase PostgreSQL via DATABASE_URL.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


def _get_database_url() -> str:
    """Convert DATABASE_URL to use psycopg3 dialect (falls back to psycopg2)."""
    url = settings.DATABASE_URL
    # Determine which driver is available
    try:
        import psycopg  # noqa: F401
        dialect = "postgresql+psycopg"
    except ImportError:
        dialect = "postgresql+psycopg2"
    if url.startswith("postgres://"):
        url = url.replace("postgres://", f"{dialect}://", 1)
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", f"{dialect}://", 1)
    return url


engine = create_engine(
    _get_database_url(),
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


def get_db():
    """Dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
