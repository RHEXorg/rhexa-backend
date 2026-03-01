from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    # App
    APP_NAME: str = "RheXa API"
    ENV: str = "development"
    DEBUG: bool = False

    # Security
    SECRET_KEY: str = "super-secret-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ENCRYPTION_KEY: str = "-uDDh3dJo44zksJUziI7Aj5pixBsMVvv2d5dMqZu4DA="

    # Database
    DATABASE_URL: str = "sqlite:///./dev.db"

    # OpenRouter (Primary LLM)
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_MODEL: str = "stepfun/step-3.5-flash:free"
    HF_TOKEN: str | None = None

    # AI / RAG
    OPENAI_API_KEY: str | None = None
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    VECTOR_DB_PATH: str = "vector_store"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # Email
    SMTP_HOST: str | None = None
    SMTP_PORT: int | None = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: str | None = None
    EMAILS_FROM_NAME: str | None = "RheXa Security"

    # Google OAuth
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str = "http://127.0.0.1:8000/api/auth/google/callback"
    FRONTEND_URL: str = "http://localhost:3000"

    # GitHub OAuth
    GITHUB_CLIENT_ID: str | None = None
    GITHUB_CLIENT_SECRET: str | None = None
    GITHUB_REDIRECT_URI: str = "http://127.0.0.1:8000/api/auth/github/callback"

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
