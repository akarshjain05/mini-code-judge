from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine, get_db
from app.routers import auth, submissions, problems, admin
from app.routers.ai_review import router as ai_review_router
from app.routers.contest import router as contest_router
from app.routers.contest import Contest, ContestProblem, ContestParticipant
from app.routers.leaderboard import router as leaderboard_router
from app.worker.poller import start_background_worker

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Mini Code Judge",
    description="Submit code, get verdicts + AI review + Contests.",
    version="3.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    # Safe column migrations using PostgreSQL's native ADD COLUMN IF NOT EXISTS
    with engine.connect() as conn:
        for sql in [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(100)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number VARCHAR(30)",
        ]:
            conn.execute(text(sql))
        conn.commit()
    start_background_worker()

app.include_router(auth.router)
app.include_router(submissions.router)
app.include_router(problems.router)
app.include_router(admin.router)
app.include_router(ai_review_router)
app.include_router(contest_router)
app.include_router(leaderboard_router)

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