

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings

# Engine: connects Python to PostgreSQL. pool_pre_ping prevents SSL unexpected closure errors
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_recycle=300)

# SessionLocal: factory for producing database sessions per request
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Modern SQLAlchemy 2.0 Base class
class Base(DeclarativeBase):
    pass

# FastAPI Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()