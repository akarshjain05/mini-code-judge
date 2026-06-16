"""
Entry point for the FastAPI application.

Run with:
    uvicorn app.main:app --reload
"""

# from fastapi import FastAPI, Depends, HTTPException
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
# ... your other existing imports ...
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine, get_db
from app.routers import auth, submissions, problems

# Create all DB tables on startup (in production, use Alembic migrations instead)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Mini Code Judge",
    description="Submit code, get verdicts. Built with FastAPI + PostgreSQL + Redis + Docker.",
    version="1.0.0",
)

# CORS — allow any origin during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://mellow-gaufre-3dd99a.netlify.app", # Production frontend
        "http://127.0.0.1:8000",                     # Local host IP
        "http://localhost:8000",],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(submissions.router)
app.include_router(problems.router)


@app.get("/", tags=["health"])
def root():
    """Health check — visit this to confirm the server is running."""
    return {"status": "ok", "message": "Code Judge is running"}


@app.get("/health")
def check_health(db: Session = Depends(get_db)):
    try:
        # Run a simple, lightweight query to test the connection
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Database connection failed: {str(e)}"
        )
