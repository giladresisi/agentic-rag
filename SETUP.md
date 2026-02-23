# Setup Guide

This guide walks you through setting up and running the complete Agentic RAG application.

## Prerequisites

Before starting, ensure you have:

### Required
- **Python 3.10+** - Backend runtime
- **Node.js 18+** - Frontend build tooling
- **Supabase account** - Database, auth, storage (https://supabase.com) - Free tier works
- **OpenAI API key** - LLM and embeddings (https://platform.openai.com)

### Optional (Recommended)
- **LangSmith account** - Observability and trace debugging (https://smith.langchain.com) - Free tier works
- **Cohere API key** - Advanced reranking (https://cohere.com) - Free tier works. Falls back to local reranker if not configured
- **Tavily API key** - Web search tool (https://tavily.com) - Free tier works. Web search gracefully degrades if not configured

### Optional (Alternative Providers)
- **OpenRouter API key** - Access to multiple LLM providers (https://openrouter.ai)
- **LM Studio** - Run local models (https://lmstudio.ai)

### Windows: Enable Symlinks for HuggingFace Model Cache

Document parsing (Docling) downloads neural network models from HuggingFace Hub and caches them at `~/.cache/huggingface/hub/`. HuggingFace's cache system uses **symlinks** to avoid re-downloading the same model files across different versions — but Windows disables symlink creation for regular users by default.

**Without symlinks**, HuggingFace falls back to copying files instead. This still works, but means the same model file may be stored multiple times on disk if multiple versions are cached.

**To enable symlinks on Windows** (recommended), do one of the following:

**Option A — Enable Developer Mode** (recommended, no admin required after):
1. Open **Settings** → **System** → **For developers**
2. Toggle **Developer Mode** on
3. Restart your terminal

**Option B — Run Python as Administrator**:
- Right-click your terminal and select **Run as administrator** before starting the backend

> **Reference:** [HuggingFace Hub cache limitations on Windows](https://huggingface.co/docs/huggingface_hub/v1.4.0/guides/manage-cache#limitations)

> **Suppress the warning without fixing it:** Add `HF_HUB_DISABLE_SYMLINKS_WARNING=1` to `backend/.env` to silence the warning if you choose not to enable symlinks. Document parsing will still work — only cache efficiency is affected.

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd agentic-rag
```

### 2. Backend Setup

#### Create and Activate Virtual Environment

**Windows (Git Bash):**
```bash
cd backend
python -m venv venv
source venv/Scripts/activate
```

**Mac/Linux:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
```

#### Install Dependencies

```bash
pip install -r requirements.txt
```

#### Pre-download Document Parsing Models

The PDF/DOCX parser (Docling) uses large neural network models (~500MB) that must be downloaded from Hugging Face before the first document upload. This is a one-time step per machine.

```bash
python -W ignore::UserWarning -c "
import tempfile, os
from docling.document_converter import DocumentConverter
pdf = b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 3 3]>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF'
with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
    f.write(pdf); tmp = f.name
try:
    converter = DocumentConverter(); converter.convert(tmp); print('Models ready')
finally:
    os.unlink(tmp)
"
```

This will take a few minutes on first run. It runs a real (minimal) PDF conversion to force all pipeline models to download — including layout models that are lazy-loaded on first use. Subsequent runs are instant (models are cached at `~/.cache/huggingface/hub/`).

> **Windows note:** See [Windows: Enable Symlinks for HuggingFace Model Cache](#windows-enable-symlinks-for-huggingface-model-cache) in Prerequisites above.

> **Note:** Simple text formats (`.txt`, `.md`, `.html`, `.json`, `.rtf`) do not use these models and will work without this step.

#### Configure Environment Variables

Copy the example file:
```bash
cp .env.example .env
```

> **Note:** Leave this file as-is for now. You'll fill in the Supabase credentials after creating your Supabase project in Step 3. You cannot obtain the URL and API keys until a project exists.

The only credential you can add immediately is your OpenAI API key:
- `OPENAI_API_KEY` — from https://platform.openai.com

Optional services can be left blank - the application will gracefully degrade functionality (e.g., web search won't work without Tavily, but other tools will).

### 3. Supabase Setup

#### Create Account and Project

> **Important:** You must create both a Supabase account **and** a new project before you can obtain credentials. The URL and API keys in Step 2 come from a specific project — they do not exist until you create one.

1. Go to https://supabase.com, sign up (or log in), and create a new project
2. During project creation you'll choose a database password — save it somewhere safe. You won't need it for this project, but you cannot recover it later.
3. Wait for the project to finish provisioning (2-3 minutes)
4. Copy your project credentials from the dashboard:
   - **Project URL**: Settings → General → Project ID. Replace the `xxxxxxxxxxxxx` placeholder in `SUPABASE_URL` with your Project ID — the full value should look like `https://<project-id>.supabase.co`
   - **Anon & Service Role keys**: Settings → API → **API Keys** section → **"Legacy anon, service_role API keys"** tab

#### Fill in Environment Variables

Now that you have your Supabase credentials, fill them into **both** `.env` files:

**`backend/.env`** — add:
- `SUPABASE_URL` — `https://<your-project-id>.supabase.co`
- `SUPABASE_ANON_KEY` — from the "Legacy anon, service_role API keys" tab
- `SUPABASE_SERVICE_ROLE_KEY` — from the "Legacy anon, service_role API keys" tab

**`frontend/.env`** — add:
- `VITE_SUPABASE_URL` (same value as `SUPABASE_URL` above)
- `VITE_SUPABASE_ANON_KEY` (same value as `SUPABASE_ANON_KEY` above)

#### Prepare SQL Tool Migration

Before running the migrations, you need to patch one migration file with a secret from your `.env`.

Open `supabase/migrations/013_sql_tool.sql` and find this line:

```sql
CREATE ROLE sql_query_role WITH LOGIN PASSWORD '***';
```

Replace `***` with the value of `SQL_QUERY_ROLE_PASSWORD` from your `backend/.env`. The line should end up looking like:

```sql
CREATE ROLE sql_query_role WITH LOGIN PASSWORD 'your_actual_password';
```

Save the file. Do **not** commit this file with a real password in it.

#### Run Database Migrations

You need to run all migration files in the `supabase/migrations/` directory in numerical order. There are two ways to do this:

**Option A - Using Supabase CLI (Recommended):**

**Install the CLI:**

*Mac/Linux:*
```bash
npm install -g supabase
```

*Windows — `npm install -g supabase` is unreliable on Windows due to file permission errors during cleanup. Use the binary directly instead:*
```bash
# Download the latest Windows binary from GitHub releases
curl -L https://github.com/supabase/cli/releases/latest/download/supabase_windows_amd64.tar.gz -o supabase.tar.gz
tar -xzf supabase.tar.gz supabase.exe

# Move it to a directory already on your PATH (npm's global bin directory works)
mv supabase.exe "$APPDATA/npm/supabase.exe"

# Verify
supabase --version
```

> **Note:** `supabase==2.9.1` in `backend/requirements.txt` is the Python Supabase client SDK — a completely separate package used by the backend to connect to Supabase. It is not the CLI and was already installed in Step 2.

**Authenticate, link, and push migrations:**
```bash
# Log in to your Supabase account (opens a browser window to complete auth)
supabase login

# Link to your project (project ref is Settings → General → Project ID)
supabase link --project-ref your-project-ref

# Push all migrations
supabase db push
```

**Option B - Manual SQL Execution:**

1. Open your Supabase project dashboard
2. Go to SQL Editor
3. Run each migration file from `supabase/migrations/` in order (001, 002, 003, etc.)
4. Copy the entire contents of each `.sql` file and execute
5. Verify each migration completes without errors before proceeding to the next

The migrations will create:
- Database schema (tables, columns, indexes)
- Row-Level Security (RLS) policies
- Storage buckets
- Database functions

#### Starting Over (Optional)

If you need to wipe the database and re-run the migrations from scratch, run `supabase/rollback_all.sql` in the **Supabase SQL Editor**. It drops all tables, functions, roles, and the pgvector extension created by the migrations. Once it completes, run `supabase db push` again as normal.

> **Note:** Remember to re-patch the `sql_query_role` password in `013_sql_tool.sql` before pushing again (see "Prepare SQL Tool Migration" above).

#### Restore SQL Tool Migration Placeholder

If you plan to commit the migration files, restore the password placeholder in `supabase/migrations/013_sql_tool.sql` so your real password is not stored in version control. Find the line you edited earlier and revert it back to:

```sql
CREATE ROLE sql_query_role WITH LOGIN PASSWORD '***';
```

The role and password already exist in your database — this change only affects the file, not the live schema.

#### Enable Storage

1. In Supabase dashboard, go to Storage
2. Verify the `documents` bucket exists (created by migrations)
3. Check that RLS policies are enabled for the bucket

#### Create Test User

Create a test user to verify authentication:
1. Go to Authentication → Users
2. Click "Add user" → "Create new user"
3. Enter email and password
4. Click "Create user"
5. Save these credentials in both `backend/.env` and `frontend/.env`, replacing the placeholders in `TEST_EMAIL` and `TEST_PASSWORD`

### 4. Frontend Setup

#### Install Dependencies

```bash
cd frontend
npm install
```

#### Configure Environment Variables

```bash
cp .env.example .env
```

> **Note:** Supabase credentials should already be filled in from Step 3. Verify `frontend/.env` also has:
- Backend API URL (default: `http://localhost:8000`)

## Running the Application

### Start Backend (Terminal 1)

> **Important:** Always run uvicorn from inside the venv — it packages large ML models (PyTorch, docling) that are only installed there. Using the system Python will cause document parsing to fail.

**Windows (Git Bash) — recommended: use venv's uvicorn directly:**
```bash
cd backend
venv/Scripts/uvicorn main:app --reload --port 8000
```

**Alternatively, activate the venv first:**
```bash
cd backend
source venv/Scripts/activate   # Windows (Git Bash)
# source venv/bin/activate      # Mac/Linux
uvicorn main:app --reload --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

**Verify:** Open http://localhost:8000/docs - you should see FastAPI's interactive API documentation.

### Start Frontend (Terminal 2)

```bash
cd frontend
npm run dev
```

**Expected output:**
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

**Verify:** Open http://localhost:5173 - you should see the login/signup page.

## Initial Testing

### 1. Authentication Flow

1. Open http://localhost:5173
2. Click "Sign Up"
3. Enter email and password
4. Submit the form
5. You should be redirected to the chat interface

### 2. Chat Interface

1. Click "New Thread" to create a conversation
2. Send a test message: "Hello, how are you?"
3. Verify you see a streaming response
4. Check that the message appears in the thread history

### 3. Document Ingestion (Optional)

1. Click on the "Docuemnts" tab
2. Upload a test document (PDF, DOCX, TXT, etc.)
3. Wait for processing to complete
4. Return to Chat tab
5. Ask a question about the uploaded document

### 4. LangSmith Traces (Optional)

If you configured `LANGSMITH_API_KEY` in `backend/.env`, run the automated trace verification tests instead of checking the dashboard manually:

```bash
cd frontend
npx playwright test langsmith-traces
```

This sends a real chat message through the UI and queries the LangSmith API to verify that a `chat_completions_stream` run was created with inputs, outputs, and a closed end_time. All 3 tests pass in ~50 seconds. The suite auto-skips if `LANGSMITH_API_KEY` is not configured.

## Verification Checklist

Use this checklist to verify your setup:

### Environment Setup
- [ ] Python venv activates without errors
- [ ] All backend dependencies installed (`pip list` shows packages)
- [ ] All frontend dependencies installed (`npm list` shows packages)
- [ ] Backend `.env` file exists with required credentials
- [ ] Frontend `.env` file exists with required credentials

### Services Running
- [ ] Backend starts with `uvicorn main:app --reload`
- [ ] FastAPI docs accessible at http://localhost:8000/docs
- [ ] Frontend starts with `npm run dev`
- [ ] Frontend accessible at http://localhost:5173
- [ ] No errors in terminal outputs

### Database & Storage
- [ ] All migrations applied successfully (check Supabase SQL Editor history)
- [ ] Tables exist: threads, messages, documents, chunks, books
- [ ] Storage bucket `documents` exists
- [ ] RLS policies enabled on all tables

### Authentication
- [ ] Can create user via Supabase dashboard
- [ ] Can sign up via frontend
- [ ] Can log in via frontend
- [ ] Can log out via frontend
- [ ] Protected endpoints reject unauthenticated requests
- [ ] RLS prevents cross-user data access

### Chat Functionality
- [ ] Can create new thread
- [ ] Can send message
- [ ] Streaming response works
- [ ] Messages save to database
- [ ] Can switch between threads
- [ ] Thread history persists after page refresh

### Document Ingestion
- [ ] Can upload document via UI
- [ ] Processing status updates in real-time
- [ ] Document appears in ingestion table
- [ ] Chunks created in database
- [ ] Duplicate uploads detected

### RAG Pipeline
- [ ] Ask question about uploaded document
- [ ] LLM retrieves relevant chunks
- [ ] Sources displayed in response
- [ ] Hybrid search combines vector + keyword
- [ ] Reranking improves result ordering

### Tool Calling
- [ ] Document retrieval tool works ("What is in my documents?")
- [ ] Text-to-SQL tool works ("What books are in the database?")
- [ ] Web search tool attempts to work ("What's the weather today?")
- [ ] Subagent delegation triggers on analysis tasks

### Observability (Optional)
- [ ] `npx playwright test langsmith-traces` — all 3 tests pass (auto-skips if no API key)

## Cloud Deployment

### Backend: Google Cloud Run

The backend is deployed to Google Cloud Run with continuous deployment wired to the `main` branch via Cloud Build.

**Live service:** `https://agentic-rag-94676406483.me-west1.run.app`

#### GCP Project Setup (one-time)

1. Create a GCP project at https://console.cloud.google.com
2. Enable the required APIs:
   ```bash
   gcloud services enable cloudbuild.googleapis.com run.googleapis.com \
     artifactregistry.googleapis.com --project=YOUR_PROJECT_ID
   ```
3. Create an Artifact Registry repository:
   ```bash
   gcloud artifacts repositories create cloud-run-source-deploy \
     --repository-format=docker --location=YOUR_REGION --project=YOUR_PROJECT_ID
   ```

#### Wire GitHub Continuous Deployment

1. Open the [Cloud Run console](https://console.cloud.google.com/run)
2. Click **Create Service** → **Continuously deploy from a repository**
3. Connect your GitHub account and select the repository
4. Set **Branch** to `main` and **Build type** to `Dockerfile`
5. Set **Dockerfile location** to `backend/Dockerfile`
6. Set **Memory** to **2 GiB** (required — default 512 MiB is insufficient for torch+docling startup)
7. Click **Create**

Every push to `main` now triggers an automatic build and deploy.

#### Configure Environment Variables

Create `.cloudrun_env.yaml` at the repo root (this file is gitignored — never commit it):

```yaml
SUPABASE_URL: https://your-project-id.supabase.co
SUPABASE_ANON_KEY: your-anon-key
SUPABASE_SERVICE_ROLE_KEY: your-service-role-key
OPENAI_API_KEY: your-openai-key
CORS_ORIGINS: https://your-app.vercel.app
LANGSMITH_API_KEY: your-langsmith-key   # optional
LANGSMITH_PROJECT: default              # optional
COHERE_API_KEY: your-cohere-key         # optional
TAVILY_API_KEY: your-tavily-key         # optional
```

Apply the env vars to the service (do this **before or immediately after** the first push — the app crashes at startup without them):

```bash
gcloud run services update SERVICE_NAME \
  --region=YOUR_REGION \
  --project=YOUR_PROJECT_ID \
  --env-vars-file=.cloudrun_env.yaml
```

Then shift traffic to the latest revision:

```bash
gcloud run services update-traffic SERVICE_NAME \
  --region=YOUR_REGION \
  --project=YOUR_PROJECT_ID \
  --to-latest
```

#### Key Configuration Notes

- **Port:** The Dockerfile CMD uses `${PORT:-8000}`. Cloud Run injects `PORT=8080` and health-checks on that port — never hardcode port 8000 in the CMD.
- **Memory:** Must be set to 2 GiB. torch+docling exceed the default 512 MiB limit during startup warmup.
- **Traffic routing:** Use `--to-latest` after any `--no-traffic` update, or new revision deployments will sit at 0% traffic.
- **Env vars file:** `.cloudrun_env.yaml` is gitignored. Regenerate it from `backend/.env` if lost. Apply it again after any key rotation.

#### Build Time

`torch`, `torchvision`, and `docling` are large ML packages (~2GB). Builds take 15–20 minutes. Docker layer caching is not enabled by default in Cloud Build, so every build reinstalls all dependencies.

Docling's neural network models download on first document upload after each new deployment (~500MB, a few minutes). Simple text formats (`.txt`, `.md`, `.json`) are unaffected.

#### Cold Starts

Cloud Run scales to zero when idle. Cold starts take 30–60 seconds as the service instance initialises. This is normal on the free tier.

## Troubleshooting

### Cloud Run Deployment Issues

**App crashes immediately on startup (Pydantic `ValidationError`)**
- **Cause:** Env vars not applied — the service only has Cloud Run's injected `PORT` variable
- **Fix:** Apply `.cloudrun_env.yaml` to the service: `gcloud run services update ... --env-vars-file=.cloudrun_env.yaml`
- **Verify:** Check Cloud Run logs; you should see `INFO: Started server process` not a traceback

**Health check fails / container times out on port 8080**
- **Cause:** Dockerfile CMD hardcodes `--port 8000` instead of using `$PORT`
- **Fix:** CMD must be: `CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]`
- **Note:** Never hardcode port 8000 in the CMD for Cloud Run; it health-checks on `PORT=8080`

**OOM killed during startup**
- **Cause:** Default Cloud Run memory (512 MiB) is insufficient for torch+docling initialisation
- **Fix:** Set memory to 2 GiB: `gcloud run services update ... --memory=2Gi`

**New revision deployed but traffic not shifting**
- **Cause:** Traffic is pinned to a specific revision (often caused by a prior `--no-traffic` flag)
- **Fix:** `gcloud run services update-traffic SERVICE --region=REGION --project=PROJECT --to-latest`

**CORS errors after deploy**
- **Fix:** Set `CORS_ORIGINS` in `.cloudrun_env.yaml` to your exact frontend URL (no trailing slash), then re-apply: `gcloud run services update ... --env-vars-file=.cloudrun_env.yaml && gcloud run services update-traffic ... --to-latest`

### Backend Won't Start

**Error: "No module named 'X'"**
- **Solution:** Ensure venv is activated, run `pip install -r requirements.txt`
- **Check:** `which python` should point to your venv

**Error: "Could not find .env file"**
- **Solution:** Copy `backend/.env.example` to `backend/.env` and fill in credentials

**Error: "Invalid Supabase credentials"**
- **Solution:** Verify URL and keys in `.env` match Supabase dashboard exactly
- **Check:** No extra spaces, quotes, or newlines in `.env` values

**CORS errors in browser console**
- **Solution:** Verify `CORS_ORIGINS` in `backend/.env` matches frontend URL
- **Default:** `http://localhost:5173`

### Frontend Won't Start

**Error: "Cannot find module"**
- **Solution:** Run `npm install` in frontend directory
- **Check:** Ensure Node.js version is 18+

**Blank page after starting**
- **Solution:** Check browser console for errors
- **Check:** Verify `frontend/.env` exists with correct Supabase credentials

**Build errors with Vite**
- **Solution:** Delete `node_modules` and `package-lock.json`, run `npm install` again

### Database Issues

**Migrations fail**
- **Solution:** Check SQL Editor in Supabase for error details
- **Fix:** Run migrations one at a time to identify which one fails
- **Common:** Ensure you're running migrations in order

**RLS policy errors**
- **Solution:** Verify policies exist in Supabase dashboard (Tables → Policies)
- **Check:** Policies should reference `auth.uid()`
- **Test:** Try accessing data with two different users

**Storage upload fails**
- **Solution:** Check storage bucket exists and has proper RLS policies
- **Check:** File size under 10MB limit (configurable in backend `.env`)

### Document Ingestion Issues

**Upload fails immediately**
- **Solution:** Check file type is supported (PDF, DOCX, PPTX, HTML, MD, TXT, CSV, JSON, XML, RTF)
- **Check:** File size under limit
- **Verify:** Storage bucket permissions

**Processing status stuck**
- **Solution:** Check backend logs for errors
- **Common:** Missing dependencies for document parsing (Docling)
- **Fix:** Reinstall requirements: `pip install -r requirements.txt`

**Duplicate detection not working**
- **Solution:** Verify content_hash column exists in documents table
- **Check:** Migration 003 applied successfully

### RAG & Tool Calling Issues

**No retrieval results**
- **Solution:** Verify chunks table has embeddings
- **Check:** `RETRIEVAL_SIMILARITY_THRESHOLD` not too high (default: 0.25)
- **Test:** Upload a simple text file, ask direct question about it

**SQL tool not working**
- **Solution:** Verify books table exists and has sample data
- **Check:** `TEXT_TO_SQL_ENABLED=true` in backend `.env`

**Web search fails**
- **Solution:** This is expected if `TAVILY_API_KEY` not configured
- **Expected:** LLM should gracefully indicate it can't access web search

**Subagent not triggering**
- **Solution:** Subagent activation is LLM-dependent, try more explicit prompts
- **Example:** "Analyze the full document X and extract..."

### LangSmith Issues

**Traces not appearing**
- **Solution:** Verify `LANGSMITH_PROJECT` in `.env` matches dashboard exactly
- **Check:** Project name is case-sensitive
- **Wait:** Traces may take 10-30 seconds to appear
- **Common:** Project name mismatch (check "All Projects" view)

**Partial traces**
- **Solution:** This is normal for streaming responses
- **Expected:** Each tool call creates a separate trace

### Performance Issues

**Slow document processing**
- **Expected:** Large files (PDFs with images) can take 30+ seconds
- **Check:** Processing happens in background, status updates via Realtime

**Slow retrieval**
- **Solution:** Verify pgvector extension installed (auto-installed by migrations)
- **Optimization:** Consider adding ivfflat index for very large document sets

**Frontend lag**
- **Solution:** Check Network tab for slow API calls
- **Check:** Backend running and not rate-limited by LLM provider

## Next Steps

Once everything is working:

1. **Explore Features**
   - Upload various document types
   - Test different query patterns
   - Experiment with tool selection
   - Review LangSmith traces

2. **Customize Configuration**
   - Adjust retrieval thresholds in `backend/.env`
   - Configure preferred LLM provider
   - Enable/disable tools as needed

3. **Production Preparation**
   - Review [PROGRESS.md](./PROGRESS.md) for known limitations
   - Read [CLAUDE.md](./CLAUDE.md) for development guidelines
   - Check "Known Limitations" in [README.md](./README.md)

## Common Development Commands

### Backend
```bash
# Start server (use venv's uvicorn to avoid system Python)
venv/Scripts/uvicorn main:app --reload --port 8000  # Windows
# venv/bin/uvicorn main:app --reload --port 8000    # Mac/Linux

# Run tests
venv/Scripts/python -m pytest

# Check installed packages
venv/Scripts/pip list

# Update dependencies
venv/Scripts/pip install -r requirements.txt --upgrade
```

### Frontend
```bash
# Development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

### Database
```bash
# Pull latest schema
supabase db pull

# Create new migration
supabase migration new migration_name

# Reset database (CAREFUL - deletes all data!)
supabase db reset
```

### Debugging
```bash
# View backend logs (verbose)
venv/Scripts/uvicorn main:app --reload --log-level debug  # Windows
# venv/bin/uvicorn main:app --reload --log-level debug    # Mac/Linux

# Check backend connectivity
curl http://localhost:8000/docs

# Check frontend build
npm run build && npm run preview
```
