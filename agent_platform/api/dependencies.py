"""
FastAPI Dependencies
Provides reusable dependencies for routes (DB session, auth, etc.)
"""

from typing import Generator
from sqlalchemy.orm import Session

from agent_platform.db.database import get_db


def get_db_session() -> Generator[Session, None, None]:
    """
    Dependency for database session.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db_session)):
            return db.query(Item).all()
    """
    with get_db() as db:
        yield db
