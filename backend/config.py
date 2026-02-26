from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from pathlib import Path

# Get the directory where this config.py file is located
BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Supabase
    SUPABASE_PROJECT_REF: str | None = None
    SUPABASE_URL: str | None = None  # Derived from SUPABASE_PROJECT_REF if not set explicitly
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str

    @model_validator(mode='after')
    def derive_supabase_url(self) -> 'Settings':
        if not self.SUPABASE_URL:
            if self.SUPABASE_PROJECT_REF:
                self.SUPABASE_URL = f"https://{self.SUPABASE_PROJECT_REF}.supabase.co"
            else:
                raise ValueError("Either SUPABASE_URL or SUPABASE_PROJECT_REF must be set")
        return self

    # OpenAI (default provider)
    OPENAI_API_KEY: str

    # OpenRouter (optional)
    OPENROUTER_API_KEY: str | None = None

    # LM Studio (optional)
    LM_STUDIO_API_KEY: str | None = None

    # Cohere (optional - for reranking)
    COHERE_API_KEY: str | None = None

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
    RETRIEVAL_LIMIT: int = 10
    RETRIEVAL_SIMILARITY_THRESHOLD: float = 0.25  # Lowered for better recall with varied LLM-generated queries

    # Hybrid Search (Module 6)
    HYBRID_SEARCH_ENABLED: bool = True
    HYBRID_VECTOR_WEIGHT: float = 0.5
    HYBRID_KEYWORD_WEIGHT: float = 0.5

    # Reranking (Module 6)
    RERANKING_ENABLED: bool = True
    RERANKING_PROVIDER: str = "local"  # Options: cohere, local
    RERANKING_TOP_N: int = 5
    RERANKING_RETRIEVAL_MULTIPLIER: int = 3  # Retrieve N*multiplier candidates for reranking
    COHERE_RERANK_MODEL: str = "rerank-english-v3.0"
    LOCAL_RERANK_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Tavily (Module 7 - Web Search)
    TAVILY_API_KEY: str | None = None
    WEB_SEARCH_ENABLED: bool = True
    WEB_SEARCH_MAX_RESULTS: int = 5

    # Text-to-SQL (Module 7)
    TEXT_TO_SQL_ENABLED: bool = True
    SQL_QUERY_ROLE_PASSWORD: str | None = None

    # Server
    PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="allow"
    )


# Initialize settings
settings = Settings()
