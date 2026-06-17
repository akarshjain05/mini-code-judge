"""
Entry point for the FastAPI application.
"""
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine, get_db
from app.routers import auth, submissions, problems, admin

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Mini Code Judge",
    description="Submit code, get verdicts.",
    version="1.0.0",
)

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
app.include_router(admin.router)

@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "message": "Code Judge is running"}

@app.get("/health")
def check_health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
