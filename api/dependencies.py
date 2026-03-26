"""
FastAPI dependency injection helpers.
"""

from typing import Generator
from scorer.database import SessionLocal


def get_db() -> Generator:
    """Yield a SQLAlchemy session, closing it when done."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
