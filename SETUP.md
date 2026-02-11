# Module 1 Setup Guide

This guide walks you through the remaining setup steps to get the application running.

## Prerequisites

- Python 3.10+
- Node.js 18+
- A Supabase account (https://supabase.com)
- An OpenAI account (https://platform.openai.com)
- A LangSmith account (https://smith.langchain.com)

## Backend Setup

### 1. Create Python Virtual Environment

```bash
cd backend
python -m venv venv
```

### 2. Activate Virtual Environment

**Windows:**
```bash
venv\Scripts\activate
```

**Mac/Linux:**
```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

- **SUPABASE_URL**: Your Supabase project URL
- **SUPABASE_ANON_KEY**: Your Supabase anon/public key
- **SUPABASE_SERVICE_ROLE_KEY**: Your Supabase service role key
- **OPENAI_API_KEY**: Your OpenAI API key
- **OPENAI_ASSISTANT_ID**: Create an assistant via OpenAI dashboard (see below)
- **LANGSMITH_API_KEY**: Your LangSmith API key

#### Creating the OpenAI Assistant

1. Go to https://platform.openai.com/assistants
2. Click "Create"
3. Name: "RAG Assistant"
4. Instructions: "You are a helpful assistant with access to file search."
5. Enable the **file_search** tool
6. Create and copy the assistant ID (starts with `asst_`)
7. Paste it into your `.env` file

## Supabase Setup

### 1. Create a New Project

1. Go to https://supabase.com
2. Create a new project
3. Copy your project URL and keys to backend `.env`

### 2. Run the Database Migration

Option A - Using Supabase CLI (recommended):
```bash
# Install Supabase CLI
npm install -g supabase

# Link to your project
supabase link --project-ref your-project-ref

# Run migration
supabase db push
```

Option B - Using SQL Editor:
1. Open your Supabase project
2. Go to SQL Editor
3. Copy the contents of `supabase/migrations/001_initial_schema.sql`
4. Paste and run it

### 3. Verify Database Setup

Check that these tables exist in your Supabase database:
- `threads`
- `messages`

Verify RLS policies are enabled for both tables.

### 4. Test Authentication

Create a test user via Supabase dashboard:
1. Go to Authentication > Users
2. Add user manually with email/password
3. Confirm the user can be created

## Frontend Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with:
- **VITE_SUPABASE_URL**: Same as backend
- **VITE_SUPABASE_ANON_KEY**: Same as backend
- **VITE_API_URL**: `http://localhost:8000`

## Running the Application

### 1. Start Backend (Terminal 1)

```bash
cd backend
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux
uvicorn main:app --reload --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

Verify API is running:
- Open http://localhost:8000/docs
- You should see FastAPI's interactive documentation

### 2. Start Frontend (Terminal 2)

```bash
cd frontend
npm run dev
```

Expected output:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5174/
  ➜  Network: use --host to expose
```

### 3. Test the Application

1. Open http://localhost:5174
2. Click "Sign Up" to create an account
3. Fill in email/password and submit
4. You should be redirected to the chat interface
5. Click "New Thread" to create a chat thread
6. Send a test message
7. Verify you see a streaming response

## Verification Checklist

Use this checklist from the plan to verify everything works:

### Foundation
- [ ] Python venv activates successfully
- [ ] `uvicorn backend.main:app --reload` starts without errors
- [ ] FastAPI docs accessible at http://localhost:8000/docs
- [ ] `npm run dev` starts frontend without errors
- [ ] Frontend accessible at http://localhost:5174
- [ ] Tailwind styles render correctly

### Database & Auth
- [ ] Supabase project created
- [ ] Migration runs successfully (tables + RLS created)
- [ ] Can create user via Supabase dashboard
- [ ] RLS prevents cross-user data access (test with 2 users)

### Auth Integration
- [ ] POST /auth/signup creates user and returns tokens
- [ ] POST /auth/login authenticates successfully
- [ ] GET /auth/me returns user info
- [ ] Protected endpoints reject unauthenticated requests
- [ ] Frontend login redirects to chat after success
- [ ] Frontend logout clears session

### OpenAI & LangSmith
- [ ] OpenAI assistant created (store assistant_id in .env)
- [ ] Can create thread via backend API
- [ ] Thread ID stored in database
- [ ] Can send message to thread
- [ ] Response received from OpenAI
- [ ] LangSmith project shows traces
- [ ] Traces include input/output and timing

### Chat Streaming
- [ ] SSE stream returns chunks in order
- [ ] Stream completes with [DONE] marker
- [ ] Message saved to database after streaming
- [ ] Frontend displays streaming text in real-time
- [ ] Multiple messages in same thread work
- [ ] Thread context maintained across messages

### End-to-End
- [ ] Sign up new user
- [ ] Create new thread
- [ ] Send first message, see streaming response
- [ ] Send follow-up message (tests continuity)
- [ ] Create second thread
- [ ] Switch between threads
- [ ] Messages persist after page refresh
- [ ] Verify trace in LangSmith for each message
- [ ] No console errors in browser or terminal

## Troubleshooting

### Backend won't start

**Error: "No module named 'dotenv'"**
- Solution: Ensure venv is activated and run `pip install -r requirements.txt`

**Error: "Could not import module 'main'"**
- Solution: Ensure you're in the `backend` directory when running uvicorn

**CORS errors**
- Solution: Check `CORS_ORIGINS` in backend `.env` matches frontend URL

### Frontend won't start

**Error: "Cannot find module"**
- Solution: Run `npm install` in frontend directory

**Blank page after npm run dev**
- Solution: Check browser console for errors, verify `.env` file exists

### Database issues

**RLS policy errors**
- Solution: Verify policies exist and use `auth.uid() = user_id`
- Test with 2 different users to ensure isolation

### OpenAI errors

**Error: "Assistant not found"**
- Solution: Verify `OPENAI_ASSISTANT_ID` is correct in `.env`
- Ensure assistant has `file_search` tool enabled

**No streaming response**
- Solution: Check LangSmith traces to see if OpenAI is being called
- Verify `LANGSMITH_TRACING=true` in `.env`

## Next Steps

Once everything is working:
1. Mark items complete in PROGRESS.md
2. Review CLAUDE.md for development guidelines
3. Prepare for Module 2 (switching from Responses API to Chat Completions API)

## Common Development Commands

### Backend
```bash
# Start server
uvicorn main:app --reload

# Run with custom port
uvicorn main:app --reload --port 8001

# Check Python version
python --version
```

### Frontend
```bash
# Development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Database
```bash
# Reset database (careful - deletes all data!)
supabase db reset

# Create new migration
supabase migration new migration_name
```
