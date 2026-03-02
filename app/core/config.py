from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    # App
    APP_NAME: str = "RheXa API"
    ENV: str = "production"
    DEBUG: bool = False
    BACKEND_URL: str = "https://rhexa-backend.vercel.app"

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
    VECTOR_DB_PATH: str = "/tmp/vector_store" if ENV == "production" else "vector_store"
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
    GOOGLE_REDIRECT_URI: str | None = None # Computed below
    FRONTEND_URL: str = "https://rhexa.com"

    # GitHub OAuth
    GITHUB_CLIENT_ID: str | None = None
    GITHUB_CLIENT_SECRET: str | None = None
    GITHUB_REDIRECT_URI: str | None = None # Computed below

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()

# Post-process redirect URIs if not provided
if not settings.GOOGLE_REDIRECT_URI:
    settings.GOOGLE_REDIRECT_URI = f"{settings.BACKEND_URL}/api/auth/google/callback"

if not settings.GITHUB_REDIRECT_URI:
    settings.GITHUB_REDIRECT_URI = f"{settings.BACKEND_URL}/api/auth/github/callback"
