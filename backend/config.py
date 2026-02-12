from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from pathlib import Path

# Get the directory where this config.py file is located
BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # OpenAI (default provider)
    OPENAI_API_KEY: str

    # Provider defaults (fallback values)
    DEFAULT_PROVIDER: str = "openai"
    DEFAULT_MODEL: str = "gpt-4o-mini"
    DEFAULT_BASE_URL: str = "https://api.openai.com/v1"

    # LangSmith (optional - for observability)
    LANGSMITH_API_KEY: str | None = None
    LANGSMITH_PROJECT: str = "default"
    LANGSMITH_TRACING: bool = True

    # Server
    PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5174"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="allow"
    )


# Initialize settings with debug output
print("\n" + "=" * 60)
print("LOADING SETTINGS FROM .ENV")
print("=" * 60)
print(f"Looking for .env at: {BASE_DIR / '.env'}")
print(f".env exists: {(BASE_DIR / '.env').exists()}")

try:
    settings = Settings()
    print(f"✓ Settings loaded successfully")
    print(f"✓ SUPABASE_URL: {'SET' if settings.SUPABASE_URL else 'NOT SET'}")
    print(f"✓ OPENAI_API_KEY: {'SET' if settings.OPENAI_API_KEY else 'NOT SET'}")
    print(f"✓ LANGSMITH_API_KEY: {'SET' if settings.LANGSMITH_API_KEY else 'NOT SET'}")
    print(f"✓ LANGSMITH_PROJECT: {settings.LANGSMITH_PROJECT}")
    print(f"✓ LANGSMITH_TRACING: {settings.LANGSMITH_TRACING}")
    print("=" * 60 + "\n")
except Exception as e:
    print(f"✗ Error loading settings: {e}")
    print("=" * 60 + "\n")
    raise
