# Initialize LangSmith tracing FIRST - before any other imports
# This must happen before routers are imported (they import openai_service)
import services.langsmith_service  # noqa: F401

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from routers import auth, chat, ingestion

app = FastAPI(title="Agentic RAG Masterclass API", version="1.0.0")

# CORS middleware
origins = settings.CORS_ORIGINS.split(",")
origins = [origin.strip() for origin in origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])


@app.get("/")
def read_root():
    return {
        "message": "Agentic RAG Masterclass API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
