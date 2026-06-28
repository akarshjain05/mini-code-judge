"""
Central Redis client — used for:
  - JWT blacklist (logout invalidation)
  - Login attempt tracking / account lockout
  - Email verification tokens
"""
import redis
from app.core.config import settings

_client: redis.Redis | None = None

def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


# ── JWT Blacklist ─────────────────────────────────────────────────────
BLACKLIST_PREFIX = "jwt:blacklist:"

def blacklist_token(jti: str, ttl_seconds: int) -> None:
    """Add a token ID to the blacklist with TTL matching token expiry."""
    get_redis().setex(f"{BLACKLIST_PREFIX}{jti}", ttl_seconds, "1")

def is_token_blacklisted(jti: str) -> bool:
    return get_redis().exists(f"{BLACKLIST_PREFIX}{jti}") > 0


# ── Account lockout ───────────────────────────────────────────────────
ATTEMPT_PREFIX  = "login:attempts:"
LOCKOUT_PREFIX  = "login:locked:"
MAX_ATTEMPTS    = 5        # lock after this many consecutive failures
LOCKOUT_SECONDS = 15 * 60  # 15 minutes
ATTEMPT_WINDOW  = 15 * 60  # reset count after 15 min of inactivity

def record_failed_login(username: str) -> int:
    """Increment failure counter. Returns new count."""
    r   = get_redis()
    key = f"{ATTEMPT_PREFIX}{username.lower()}"
    count = r.incr(key)
    r.expire(key, ATTEMPT_WINDOW)
    if count >= MAX_ATTEMPTS:
        r.setex(f"{LOCKOUT_PREFIX}{username.lower()}", LOCKOUT_SECONDS, "1")
    return count

def clear_failed_logins(username: str) -> None:
    r = get_redis()
    r.delete(f"{ATTEMPT_PREFIX}{username.lower()}")
    r.delete(f"{LOCKOUT_PREFIX}{username.lower()}")

def is_account_locked(username: str) -> bool:
    return get_redis().exists(f"{LOCKOUT_PREFIX}{username.lower()}") > 0

def lockout_ttl(username: str) -> int:
    """Remaining lockout seconds."""
    return get_redis().ttl(f"{LOCKOUT_PREFIX}{username.lower()}")


# ── Email verification tokens ─────────────────────────────────────────
VERIFY_PREFIX = "email:verify:"
VERIFY_TTL    = 24 * 60 * 60  # 24 hours

def store_verification_token(token: str, user_id: int) -> None:
    get_redis().setex(f"{VERIFY_PREFIX}{token}", VERIFY_TTL, str(user_id))

def consume_verification_token(token: str) -> int | None:
    """Returns user_id and deletes token, or None if not found/expired."""
    r   = get_redis()
    key = f"{VERIFY_PREFIX}{token}"
    val = r.get(key)
    if val is None:
        return None
    r.delete(key)
    return int(val)