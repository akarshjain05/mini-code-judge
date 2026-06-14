from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# Engine: connects Python to PostgreSQL
engine = create_engine(settings.DATABASE_URL)

# SessionLocal: each request gets its own DB session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base: all SQLAlchemy models inherit from this
Base = declarative_base()


def get_db():
    """
    FastAPI dependency — yields a DB session per request,
    then closes it automatically when the request finishes.

    Usage in a route:
        def my_route(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
