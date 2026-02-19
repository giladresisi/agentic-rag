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

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd agentic-rag
```

### 2. Backend Setup

#### Create and Activate Virtual Environment

**Windows:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate
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

#### Configure Environment Variables

Copy the example file:
```bash
cp .env.example .env
```

Edit `backend/.env` and fill in your credentials. The file contains placeholders for all required and optional services. At minimum, you need:
- Supabase credentials (URL, anon key, service role key)
- OpenAI API key

Optional services can be left blank - the application will gracefully degrade functionality (e.g., web search won't work without Tavily, but other tools will).

### 3. Supabase Setup

#### Create Project

1. Go to https://supabase.com and create a new project
2. Wait for the project to finish provisioning (2-3 minutes)
3. Copy your project credentials:
   - Project URL (Settings → API → Project URL)
   - Anon/Public Key (Settings → API → anon public)
   - Service Role Key (Settings → API → service_role)
4. Add these to `backend/.env`

#### Run Database Migrations

You need to run all migration files in the `supabase/migrations/` directory in numerical order. There are two ways to do this:

**Option A - Using Supabase CLI (Recommended):**

```bash
# Install Supabase CLI globally
npm install -g supabase

# Link to your project (you'll need your project ref from Supabase dashboard)
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
5. Keep these credentials for testing

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

Edit `frontend/.env` with:
- Your Supabase URL and anon key (same as backend)
- Backend API URL (default: `http://localhost:8000`)

## Running the Application

### Start Backend (Terminal 1)

```bash
cd backend
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux
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

1. Click on the "Ingestion" tab
2. Upload a test document (PDF, DOCX, TXT, etc.)
3. Wait for processing to complete
4. Return to Chat tab
5. Ask a question about the uploaded document

### 4. LangSmith Traces (Optional)

If you configured LangSmith:
1. Go to https://smith.langchain.com
2. Open your project (default: "default")
3. Look for traces from your test messages
4. Verify input, output, and timing are captured

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
- [ ] LangSmith traces appear in dashboard
- [ ] Traces include input, output, timing
- [ ] Tool calls visible in traces
- [ ] Errors captured in traces

## Troubleshooting

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
# Start server
uvicorn main:app --reload --port 8000

# Run tests
python -m pytest

# Check installed packages
pip list

# Update dependencies
pip install -r requirements.txt --upgrade
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
uvicorn main:app --reload --log-level debug

# Check backend connectivity
curl http://localhost:8000/docs

# Check frontend build
npm run build && npm run preview
```
