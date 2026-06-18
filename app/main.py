"""Entry point for the FastAPI application."""
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine, get_db
from app.routers import auth, submissions, problems, admin
from app.routers.ai_review import router as ai_review_router
from app.routers.contest import router as contest_router
from app.routers.run import router as run_router
from app.worker.poller import start_background_worker

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mini Code Judge", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    start_background_worker()

app.include_router(auth.router)
app.include_router(submissions.router)
app.include_router(problems.router)
app.include_router(admin.router)
app.include_router(ai_review_router)
app.include_router(contest_router)
app.include_router(run_router)

@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "message": "Code Judge is running"}

@app.get("/health")
def check_health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
