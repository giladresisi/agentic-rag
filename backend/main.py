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
import threading

class _RapidOCRWarningFilter(logging.Filter):
    def filter(self, record):
        return record.levelno >= logging.WARNING

logging.getLogger("RapidOCR").addFilter(_RapidOCRWarningFilter())


logger = logging.getLogger(__name__)

_warmup_state: dict = {"ready": False, "error": None}


def _background_warmup() -> None:
    """Run DocumentConverter warm-up in a thread so startup is non-blocking."""
    from services.embedding_service import warmup_converter
    try:
        warmup_converter()
        _warmup_state["ready"] = True
    except Exception as e:
        _warmup_state.update({"error": str(e), "ready": True})  # unblock upload even on error
        logger.warning(
            "Docling warmup failed — PDF/DOCX parsing will fail until this is resolved. "
            "Error: %s", e
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start Docling warm-up in a background thread so the server is immediately
    # ready to serve auth/chat requests. Upload UI polls /health/warmup and
    # stays disabled until this thread sets _warmup_state["ready"] = True.
    threading.Thread(target=_background_warmup, daemon=True).start()
    yield


app = FastAPI(title="IR Copilot API", version="1.0.0", lifespan=lifespan)

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
        "message": "IR Copilot API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/health/warmup")
def warmup_status():
    return _warmup_state
