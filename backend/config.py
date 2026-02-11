from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_ASSISTANT_ID: str

    # LangSmith
    LANGSMITH_API_KEY: str
    LANGSMITH_PROJECT: str = "rag-masterclass-module1"
    LANGSMITH_TRACING: bool = True

    # Server
    PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5174"

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


settings = Settings()
