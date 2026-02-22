# Suppress Pydantic protected-namespace warnings emitted by docling's internal models.
# These are a docling packaging issue (their fields are named model_*) and are harmless.
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic._internal._fields")

# Initialize LangSmith tracing FIRST - before any other imports
# This must happen before routers are imported (they import openai_service)
import services.langsmith_service  # noqa: F401

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from routers import auth, chat, ingestion

# Suppress RapidOCR INFO logs via a Filter — immune to rapidocr's Logger.__init__
# resetting the level to INFO on every import/re-import. Filters are never cleared
# by setLevel(), so this persists regardless of what rapidocr does internally.
import logging

class _RapidOCRWarningFilter(logging.Filter):
    def filter(self, record):
        return record.levelno >= logging.WARNING

logging.getLogger("RapidOCR").addFilter(_RapidOCRWarningFilter())


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm up docling's DocumentConverter at startup.
    # Docling downloads its ML models (layout, tableformer, OCR) lazily on first use.
    # Without this, a partial/interrupted HuggingFace download is only discovered
    # mid-upload — failing silently for the end user. Warming up here ensures:
    #   1. Models are downloaded once at boot (not during a user's first upload).
    #   2. Any model issue surfaces as a visible WARNING rather than a silent per-upload failure.
    #   3. The DocumentConverter singleton is ready before the first request.
    # Non-fatal: a warmup failure logs a warning but does not prevent the server from starting,
    # so auth/chat endpoints still work even if docling has a model issue.
    from services.embedding_service import warmup_converter
    try:
        warmup_converter()
    except Exception as e:
        logger.warning(
            "Docling warmup failed — PDF/DOCX parsing will fail until this is resolved. "
            "Run 'python -c \"from docling.document_converter import DocumentConverter; DocumentConverter()\"' "
            "in the venv to diagnose. Error: %s", e
        )
    yield


app = FastAPI(title="Agentic RAG API", version="1.0.0", lifespan=lifespan)

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
        "message": "Agentic RAG API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
