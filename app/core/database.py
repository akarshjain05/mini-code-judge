# from sqlalchemy import create_engine
# from sqlalchemy.orm import declarative_base, sessionmaker

# from app.core.config import settings

# # Engine: connects Python to PostgreSQL
# engine = create_engine(settings.DATABASE_URL)

# # SessionLocal: each request gets its own DB session
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# # Base: all SQLAlchemy models inherit from this
# Base = declarative_base()


# def get_db():
#     """
#     FastAPI dependency — yields a DB session per request,
#     then closes it automatically when the request finishes.

#     Usage in a route:
#         def my_route(db: Session = Depends(get_db)):
#             ...
#     """
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

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