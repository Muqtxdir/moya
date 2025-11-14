"""
Database configuration and session management for MOYA for Research.

Uses SQLAlchemy with SQLite for local storage.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from moya_for_research.config import settings
from loguru import logger

# Create engine with proper SQLite settings
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={
        "check_same_thread": False,  # Allow multi-threading
        "timeout": 30,  # 30 second timeout for locks
    },
    pool_pre_ping=True,  # Verify connections before use
    echo=settings.DEBUG,  # Disable SQL query logging
)


# Enable SQLite pragmas for better performance and data integrity
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Set SQLite pragmas on connection."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")  # Enable foreign key constraints
    cursor.execute(
        "PRAGMA journal_mode=WAL"
    )  # Write-Ahead Logging for better concurrency
    cursor.close()
    logger.debug("SQLite pragmas set: foreign_keys=ON, journal_mode=WAL")


# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Session:
    """
    Dependency for FastAPI routes to get database session.

    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database tables.

    Call this on application startup to create all tables.
    """

    Base.metadata.create_all(bind=engine)
    logger.info(f"Database initialized at {settings.DATABASE_URL}")


def get_session() -> Session:
    """
    Get a database session for use outside of FastAPI (e.g., in tools).

    Remember to close the session when done:
        session = get_session()
        try:
            # use session
        finally:
            session.close()
    """
    return SessionLocal()
