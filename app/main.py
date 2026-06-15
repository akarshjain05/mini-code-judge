"""
Entry point for the FastAPI application.

Run with:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine
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
    allow_origins=["https://mellow-gaufre-3dd99a.netlify.app"],
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
