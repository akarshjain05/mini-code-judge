"""
Entry point for the FastAPI application.

Run with:
    uvicorn app.main:app --reload
"""

# from fastapi import FastAPI, Depends, HTTPException
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.worker.poller import start_background_worker
# ... your other existing imports ...
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine, get_db
from app.routers import auth, submissions, problems

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Mini Code Judge",
    description="Submit code, get verdicts. Built with FastAPI + PostgreSQL + Redis + Docker.",
    version="1.0.0",
)
@app.on_event("startup")
def on_startup():
    start_background_worker()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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