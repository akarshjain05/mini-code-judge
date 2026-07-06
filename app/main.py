from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.database import Base, engine, get_db
from app.routers import auth, submissions, problems, admin
from app.routers.ai_review import router as ai_review_router
from app.routers.contest import router as contest_router
from app.routers.contest import Contest, ContestProblem, ContestParticipant
from app.routers.leaderboard import router as leaderboard_router
from app.worker.poller import start_background_worker

Base.metadata.create_all(bind=engine)

# ── Rate Limiter ───────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

app = FastAPI(
    title="Mini Code Judge",
    description="Submit code, get verdicts + AI review + Contests.",
    version="3.2.0",
)

# Attach rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── CORS — only allow the real frontend ───────────────────────────────
origins = [
    settings.FRONTEND_URL,
    "https://mini-code-judge-frontend.onrender.com",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "null",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Security headers middleware ────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"]    = "nosniff"
    response.headers["X-Frame-Options"]           = "DENY"
    response.headers["Referrer-Policy"]           = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"]        = "geolocation=(), camera=(), microphone=()"
    # Only set HSTS on HTTPS (Render always uses HTTPS in production)
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.on_event("startup")
def on_startup():
    # Safe column migrations using PostgreSQL's native ADD COLUMN IF NOT EXISTS
    with engine.connect() as conn:
        for sql in [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(100)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number VARCHAR(30)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS github_id VARCHAR(255)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE submissions ADD COLUMN IF NOT EXISTS ai_review TEXT",
            "ALTER TABLE submissions ADD COLUMN IF NOT EXISTS judged_at TIMESTAMPTZ",
            "ALTER TABLE submissions ADD COLUMN IF NOT EXISTS is_sample_only BOOLEAN NOT NULL DEFAULT FALSE",
        ]:
            conn.execute(text(sql))
        # Add unique index for github_id if not exists
        conn.execute(text("""
            DO $$ BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_indexes WHERE tablename='users' AND indexname='ix_users_github_id'
              ) THEN
                CREATE UNIQUE INDEX ix_users_github_id ON users(github_id) WHERE github_id IS NOT NULL;
              END IF;
            END $$;
        """))
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