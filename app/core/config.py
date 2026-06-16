from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Database (explicitly using psycopg2 driver)
    DATABASE_URL: str = "postgresql+psycopg2://judge_user:judge_pass@localhost:5432/judge_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # JWT Authentication Settings
    SECRET_KEY: str = "change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours (60 * 24)

    # Execution limits (enforced inside Docker for the online judge)
    TIME_LIMIT_SECONDS: int = 2
    MEMORY_LIMIT_MB: int = 256

    # Modern Pydantic V2 Config
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()