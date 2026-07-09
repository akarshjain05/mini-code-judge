from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import uuid
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.core.database import Base, engine, get_db
from app.core.logger import request_id_var, get_logger
from app.routers import auth, submissions, problems, admin
from app.routers.ai_review import router as ai_review_router
from app.routers.contest import router as contest_router
from app.routers.contest import Contest, ContestProblem, ContestParticipant
from app.routers.leaderboard import router as leaderboard_router

# ── Rate Limiter ───────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
log = get_logger(__name__)

app = FastAPI(
    title="Mini Code Judge",
    description="Submit code, get verdicts + AI review + Contests.",
    version="3.2.0",
)

# Attach rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# --- Metrics ---
Instrumentator().instrument(app).expose(app)

# ── CORS — only allow the real frontend ───────────────────────────────
origins = [
    settings.FRONTEND_URL,
    "https://mini-code-judge-frontend.onrender.com",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# ── Security headers middleware ────────────────────────────────────────
@app.middleware("http")
async def request_id_and_logging_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request_id_var.set(req_id)
    
    log.info("request_started", method=request.method, url=str(request.url))
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = req_id
    
    log.info("request_finished", status_code=response.status_code)
    return response

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
    # Database schema is now managed by Alembic migrations
    pass


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