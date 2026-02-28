# Docling Warmup Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Eliminate ~42-second cold-start delays by baking Docling ML models into the Docker image, making startup non-blocking, and showing an upload-blocked banner in the UI until the model engine is ready.

**Architecture:** The Dockerfile pre-downloads models at build time so runtime startup only loads them from disk (~5-10s). `main.py` starts the model warm-up in a background thread and immediately accepts requests. A new `GET /health/warmup` endpoint exposes readiness. The frontend polls that endpoint every 2s and disables the upload UI with an explanatory banner until `ready: true`.

**Tech Stack:** Python threading, FastAPI, React, TypeScript, Tailwind CSS, lucide-react

---

### Task 1: Pre-bake Docling models into Docker image

**Files:**
- Modify: `backend/Dockerfile`

**Step 1: Open the Dockerfile and locate the `uv sync` line**

Read `backend/Dockerfile`. The relevant section is:
```dockerfile
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .
```

**Step 2: Add model pre-download step after `uv sync`**

Insert the following block between `RUN uv sync` and `COPY . .`:
```dockerfile
# Pre-download Docling ML models at image build time.
# Models land in /root/.cache/huggingface/ as a cached layer.
# Rebuilds only when pyproject.toml / uv.lock changes.
RUN /app/.venv/bin/python -c \
    "from docling.document_converter import DocumentConverter; DocumentConverter()"
```

The Dockerfile should now look like:
```dockerfile
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
# Rebuilds only when pyproject.toml / uv.lock changes.
RUN /app/.venv/bin/python -c \
    "from docling.document_converter import DocumentConverter; DocumentConverter()"

# Copy application source
COPY . .

EXPOSE 8080

ENV PATH="/app/.venv/bin:$PATH"

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

**Step 3: Commit**
```bash
git add backend/Dockerfile
git commit -m "feat(docker): pre-bake Docling ML models at image build time"
```

---

### Task 2: Non-blocking warmup + `/health/warmup` endpoint

**Files:**
- Modify: `backend/main.py`
- Create: `backend/tests/auto/test_warmup_endpoint.py`

**Step 1: Write the failing test first**

Create `backend/tests/auto/test_warmup_endpoint.py`:
```python
"""Tests for /health/warmup endpoint."""
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_warmup_endpoint_returns_correct_structure(client):
    """GET /health/warmup returns {ready: bool, error: str|null}."""
    response = client.get("/health/warmup")
    assert response.status_code == 200
    data = response.json()
    assert "ready" in data
    assert isinstance(data["ready"], bool)
    assert "error" in data
    assert data["error"] is None or isinstance(data["error"], str)


def test_warmup_endpoint_no_auth_required(client):
    """Warmup status is public — no Authorization header needed."""
    response = client.get("/health/warmup")
    assert response.status_code == 200
```

**Step 2: Run the test to verify it fails (endpoint doesn't exist yet)**

Run from `backend/` directory:
```bash
cd backend && uv run pytest tests/auto/test_warmup_endpoint.py -v
```
Expected: FAIL — `404 Not Found` for `/health/warmup`

**Step 3: Update `main.py`**

Open `backend/main.py`. Make these changes:

3a. Add `import threading` after the existing `import logging` line (around line 19):
```python
import logging
import threading
```

3b. Add the warmup state dict and background function immediately before the `lifespan` function (after the `logger = logging.getLogger(__name__)` line):
```python
_warmup_state: dict = {"ready": False, "error": None}


def _background_warmup() -> None:
    """Run DocumentConverter warm-up in a thread so startup is non-blocking."""
    from services.embedding_service import warmup_converter
    try:
        warmup_converter()
        _warmup_state["ready"] = True
    except Exception as e:
        _warmup_state["error"] = str(e)
        _warmup_state["ready"] = True  # unblock upload even on error
        logger.warning(
            "Docling warmup failed — PDF/DOCX parsing will fail until this is resolved. "
            "Error: %s", e
        )
```

3c. Replace the entire `lifespan` function with:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start Docling warm-up in a background thread so the server is immediately
    # ready to serve auth/chat requests. Upload UI polls /health/warmup and
    # stays disabled until this thread sets _warmup_state["ready"] = True.
    threading.Thread(target=_background_warmup, daemon=True).start()
    yield
```

3d. Add the new endpoint after the existing `/health` endpoint at the bottom of the file:
```python
@app.get("/health/warmup")
def warmup_status():
    return _warmup_state
```

**Step 4: Run the test to verify it passes**
```bash
cd backend && uv run pytest tests/auto/test_warmup_endpoint.py -v
```
Expected: PASS — both tests green

**Step 5: Also verify the existing health check still passes**
```bash
cd backend && uv run pytest tests/auto/ -v -k "health or warmup"
```

**Step 6: Commit**
```bash
git add backend/main.py backend/tests/auto/test_warmup_endpoint.py
git commit -m "feat(backend): non-blocking Docling warmup + GET /health/warmup endpoint"
```

---

### Task 3: `useWarmup` hook

**Files:**
- Create: `frontend/src/hooks/useWarmup.ts`

**Step 1: Create the hook**

Create `frontend/src/hooks/useWarmup.ts`:
```typescript
import { useState, useEffect, useRef } from 'react';
import { API_URL } from '@/lib/api';

/**
 * Polls GET /health/warmup every 2 seconds until the backend signals ready.
 * Stops polling once ready — never restarts in the same session.
 */
export function useWarmup() {
  const [isReady, setIsReady] = useState(false);
  const intervalRef = useRef<number | null>(null);

  useEffect(() => {
    const check = async () => {
      try {
        const response = await fetch(`${API_URL}/health/warmup`);
        if (response.ok) {
          const data = await response.json();
          if (data.ready) {
            setIsReady(true);
            if (intervalRef.current !== null) {
              clearInterval(intervalRef.current);
              intervalRef.current = null;
            }
          }
        }
      } catch {
        // Backend not reachable yet — keep polling
      }
    };

    check(); // immediate first check
    intervalRef.current = window.setInterval(check, 2000);

    return () => {
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  return { isReady };
}
```

**Step 2: Verify TypeScript compiles (no test needed for this hook — it's pure polling)**
```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors

**Step 3: Commit**
```bash
git add frontend/src/hooks/useWarmup.ts
git commit -m "feat(frontend): useWarmup hook polls /health/warmup until ready"
```

---

### Task 4: Warmup banner in `DocumentUpload`

**Files:**
- Modify: `frontend/src/components/Ingestion/DocumentUpload.tsx`

**Step 1: Add `isWarmingUp` to props interface**

In `DocumentUpload.tsx`, find the `DocumentUploadProps` interface (around line 35):
```typescript
interface DocumentUploadProps {
  onUpload: (file: File, embeddingConfig?: ProviderConfig) => Promise<void>;
  isUploading: boolean;
  embeddingConfig?: ProviderConfig;
}
```
Replace with:
```typescript
interface DocumentUploadProps {
  onUpload: (file: File, embeddingConfig?: ProviderConfig) => Promise<void>;
  isUploading: boolean;
  embeddingConfig?: ProviderConfig;
  isWarmingUp?: boolean;
}
```

**Step 2: Add `Loader2` to lucide imports**

Find the import line (line 3):
```typescript
import { Upload, FileText, X } from 'lucide-react';
```
Replace with:
```typescript
import { Upload, FileText, X, Loader2 } from 'lucide-react';
```

**Step 3: Destructure `isWarmingUp` in the component signature**

Find the function signature (line 41):
```typescript
export function DocumentUpload({ onUpload, isUploading, embeddingConfig }: DocumentUploadProps) {
```
Replace with:
```typescript
export function DocumentUpload({ onUpload, isUploading, embeddingConfig, isWarmingUp = false }: DocumentUploadProps) {
```

**Step 4: Add the warming-up banner inside the Card, before the existing content**

Find the opening of the `return` JSX in DocumentUpload (around line 313):
```tsx
  return (
    <>
      <Card className="p-6">
        <h2 className="text-lg font-semibold mb-4">Upload Documents</h2>
```
Replace with:
```tsx
  return (
    <>
      <Card className="p-6">
        <h2 className="text-lg font-semibold mb-4">Upload Documents</h2>

        {isWarmingUp && (
          <div className="flex items-start gap-3 p-3 rounded-md bg-muted border border-border mb-4">
            <Loader2 className="w-4 h-4 mt-0.5 animate-spin flex-shrink-0 text-muted-foreground" />
            <div>
              <p className="text-sm font-medium">Document processing engine is initializing</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                First start after deployment takes ~15 seconds. Upload will be available shortly.
              </p>
            </div>
          </div>
        )}
```

**Step 5: Gate all interactive elements on `isWarmingUp`**

Find the empty-queue drag zone with the `Browse Files` button. The `<div>` that wraps the drag zone has `onDragOver/onDragLeave/onDrop`. The `<input>` and `<Button>` inside it use `disabled={isUploading}`. Update all three:

For the drag handlers — wrap the entire drop zone `<div>` with a conditional. Find (around line 318):
```tsx
        {fileQueue.length === 0 ? (
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              isDragging
                ? 'border-primary bg-primary/5'
                : 'border-muted-foreground/25 hover:border-primary/50'
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
```
Replace with:
```tsx
        {fileQueue.length === 0 ? (
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              isWarmingUp
                ? 'border-muted-foreground/15 opacity-40 pointer-events-none'
                : isDragging
                  ? 'border-primary bg-primary/5'
                  : 'border-muted-foreground/25 hover:border-primary/50'
            }`}
            onDragOver={isWarmingUp ? undefined : handleDragOver}
            onDragLeave={isWarmingUp ? undefined : handleDragLeave}
            onDrop={isWarmingUp ? undefined : handleDrop}
          >
```

Find the `Browse Files` button `disabled` prop (around line 349):
```tsx
              disabled={isUploading}
```
Replace with:
```tsx
              disabled={isUploading || isWarmingUp}
```

Find the `Upload All` button `disabled` condition (around line 402):
```tsx
                disabled={
                  currentUploadIndex >= 0 ||
                  fileQueue.every(f => f.validationError || f.status !== 'pending')
                }
```
Replace with:
```tsx
                disabled={
                  isWarmingUp ||
                  currentUploadIndex >= 0 ||
                  fileQueue.every(f => f.validationError || f.status !== 'pending')
                }
```

Find the `Add More Files` button `disabled` prop (around line 396):
```tsx
                disabled={currentUploadIndex >= 0}
```
Replace with:
```tsx
                disabled={isWarmingUp || currentUploadIndex >= 0}
```

Find the `file-input-add` hidden input `disabled` prop:
```tsx
              disabled={currentUploadIndex >= 0}
```
Replace with:
```tsx
              disabled={isWarmingUp || currentUploadIndex >= 0}
```

**Step 6: Verify TypeScript compiles**
```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors

**Step 7: Commit**
```bash
git add frontend/src/components/Ingestion/DocumentUpload.tsx
git commit -m "feat(ui): disable upload with warmup banner when backend is initializing"
```

---

### Task 5: Wire `useWarmup` into `IngestionInterface`

**Files:**
- Modify: `frontend/src/components/Ingestion/IngestionInterface.tsx`

**Step 1: Import `useWarmup`**

Find the import block at the top of `IngestionInterface.tsx`. After the last hook import, add:
```typescript
import { useWarmup } from '@/hooks/useWarmup';
```

**Step 2: Call the hook inside the component**

Find the existing hooks at the top of `IngestionInterface` function body (around line 15):
```typescript
  const { user, token, logout } = useAuth();
  const {
```
Add `useWarmup` call before the `useIngestion` call:
```typescript
  const { user, token, logout } = useAuth();
  const { isReady: isWarmupReady } = useWarmup();
  const {
```

**Step 3: Pass `isWarmingUp` to `DocumentUpload`**

Find the `<DocumentUpload>` JSX (around line 111):
```tsx
            <DocumentUpload
              onUpload={handleUpload}
              isUploading={isUploading}
              embeddingConfig={modelConfig.embeddingsConfig.current}
            />
```
Replace with:
```tsx
            <DocumentUpload
              onUpload={handleUpload}
              isUploading={isUploading}
              embeddingConfig={modelConfig.embeddingsConfig.current}
              isWarmingUp={!isWarmupReady}
            />
```

**Step 4: Verify TypeScript compiles**
```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors

**Step 5: Commit**
```bash
git add frontend/src/components/Ingestion/IngestionInterface.tsx
git commit -m "feat(ui): poll warmup status and block upload until backend is ready"
```

---

### Task 6: End-to-end verification

**Step 1: Start the backend locally**
```bash
cd backend && uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Step 2: Immediately after startup, check warmup endpoint**
In a second terminal, while the server is starting:
```bash
curl http://localhost:8000/health/warmup
```
Expected within first few seconds: `{"ready": false, "error": null}`
Expected after ~10-15s: `{"ready": true, "error": null}`

**Step 3: Start frontend**
```bash
cd frontend && npm run dev
```
Navigate to `http://localhost:5173/ingestion`.

**Step 4: Verify the banner**
- Within the first 10-15 seconds after backend starts: the "Document processing engine is initializing" banner should be visible on the Upload Documents card, all buttons disabled.
- After warmup completes: banner disappears, upload controls become interactive.

**Step 5: Run backend test suite to confirm no regressions**
```bash
cd backend && uv run pytest tests/auto/ -v
```
Expected: all existing tests pass + 2 new warmup tests pass

**Step 6: Final commit if any cleanup needed**
```bash
git add -p  # stage only relevant changes
git commit -m "chore: post-verification cleanup"
```
