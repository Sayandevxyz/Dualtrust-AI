"""Database setup — SQLAlchemy engine and session factory with SQLite & PostgreSQL support."""
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

logger = logging.getLogger(__name__)

url = settings.DATABASE_URL

if url.startswith("sqlite"):
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False},
    )
else:
    try:
        engine = create_engine(
            url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        # Test connection
        with engine.connect() as conn:
            pass
    except Exception as e:
        logger.warning(f"Could not connect to PostgreSQL at {url}: {e}. Falling back to SQLite local database.")
        sqlite_url = "sqlite:///./dualtrust.db"
        engine = create_engine(
            sqlite_url,
            connect_args={"check_same_thread": False},
        )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
