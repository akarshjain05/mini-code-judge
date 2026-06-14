from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://judge_user:judge_pass@localhost:5432/judge_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # JWT
    SECRET_KEY: str = "change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Execution limits (enforced inside Docker)
    TIME_LIMIT_SECONDS: int = 2
    MEMORY_LIMIT_MB: int = 256

    class Config:
        env_file = ".env"


settings = Settings()
