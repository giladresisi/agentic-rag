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

    # OpenRouter (optional)
    OPENROUTER_API_KEY: str | None = None

    # LM Studio (optional)
    LM_STUDIO_API_KEY: str | None = None

    # Provider defaults (fallback values)
    DEFAULT_PROVIDER: str = "openai"
    DEFAULT_MODEL: str = "gpt-4o-mini"
    DEFAULT_BASE_URL: str = "https://api.openai.com/v1"

    # LangSmith (optional - for observability)
    LANGSMITH_API_KEY: str | None = None
    LANGSMITH_PROJECT: str = "default"
    LANGSMITH_TRACING: bool = True

    # Embeddings
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MAX_FILE_SIZE_MB: int = 10
    # IMPORTANT: Keep in sync with frontend/src/components/Ingestion/DocumentUpload.tsx SUPPORTED_TYPES
    SUPPORTED_FILE_TYPES: str = "pdf,docx,pptx,html,md,txt,csv,json,xml,rtf"

    # Retrieval
    RETRIEVAL_LIMIT: int = 5
    RETRIEVAL_SIMILARITY_THRESHOLD: float = 0.25  # Lowered for better recall with varied LLM-generated queries

    # Server
    PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="allow"
    )


# Initialize settings with debug output
print("\n" + "=" * 60)
print("LOADING SETTINGS FROM .ENV")
print("=" * 60)

try:
    settings = Settings()
    print("[OK] Settings loaded successfully")
    print("=" * 60 + "\n")
except Exception as e:
    print(f"[ERROR] Error loading settings: {e}")
    print("=" * 60 + "\n")
    raise
