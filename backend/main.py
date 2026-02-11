from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from routers import auth, chat

app = FastAPI(title="Agentic RAG Masterclass API", version="1.0.0")

# Add request logging middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        print(f"REQUEST: {request.method} {request.url}")
        print(f"Origin header: {request.headers.get('origin', 'MISSING')}")
        response = await call_next(request)
        print(f"Response status: {response.status_code}")
        return response

app.add_middleware(LoggingMiddleware)

# CORS middleware
origins = settings.CORS_ORIGINS.split(",")
print(f"DEBUG - CORS_ORIGINS from env: {settings.CORS_ORIGINS}")
print(f"DEBUG - Parsed origins list: {origins}")

# Strip whitespace from each origin
origins = [origin.strip() for origin in origins]
print(f"DEBUG - Cleaned origins: {origins}")

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
