FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# System dependencies required by torch (OpenMP) and docling (PDF/image processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libglib2.0-0 \
    libgl1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (separate layer for caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Pre-download Docling ML models at image build time.
# Models land in /root/.cache/huggingface/ as a cached layer.
# This layer is invalidated when pyproject.toml or uv.lock changes
# (i.e., when dependencies are updated).
RUN /app/.venv/bin/python -c \
    "from docling.document_converter import DocumentConverter; DocumentConverter()"

# Copy application source
COPY . .

EXPOSE 8080

ENV PATH="/app/.venv/bin:$PATH"

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
