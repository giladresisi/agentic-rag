# Supabase Region Migration Guide

## Problem

Your current Supabase project is in a region that doesn't support the pgvector extension, which is required for document embeddings and vector similarity search.

## Solution

Create a new Supabase project in a supported region and migrate your existing setup.

---

## Pre-Migration Checklist

Before starting, gather this information from your **current** project:

- [ ] Current project URL: `https://[project-id].supabase.co`
- [ ] Current anon key (for reference)
- [ ] Test user credentials: test@test.com / 123456

---

## Part 1: Create New Supabase Project

### Step 1: Create Project in Supported Region

1. Go to https://app.supabase.com
2. Click **New Project**
3. Configure project:
   - **Name:** `agentic-rag-masterclass` (or your preferred name)
   - **Database Password:** Choose a strong password and **save it securely**
   - **Region:** Choose a region that supports pgvector
     - **Supported regions (as shown in Supabase dashboard):**
       - `us-east-1` (US East - N. Virginia)
       - `us-east-2` (US East - Ohio)
       - `us-west-2` (US West - Oregon)
       - `eu-central-1` (Europe - Frankfurt)
       - `ap-southeast-2` (Asia Pacific - Sydney)
     - **Note:** Check your Supabase dashboard for the current list of supported regions
   - **Pricing Plan:** Free tier is fine for development
4. Click **Create new project**
5. Wait for project to provision (2-3 minutes)

### Step 2: Get New Project Credentials

Once provisioning completes:

1. Go to **Project Settings** > **API**
2. Copy and save these values:
   - **Project URL:** `https://[new-project-id].supabase.co`
   - **anon/public key:** (labeled "anon public")
   - **service_role key:** (labeled "service_role" - keep this secret!)

---

## Part 2: Apply Database Migrations

### Step 3: Apply All Migrations in Order

Go to **SQL Editor** in your new Supabase dashboard and run each migration file in order:

#### Migration 001: Initial Schema (Threads & Messages)

Copy and paste the **entire contents** of `supabase/migrations/001_initial_schema.sql`

Click **Run** ✅

#### Migration 002: Remove Assistants API Fields

Copy and paste the **entire contents** of `supabase/migrations/002_remove_assistants_api_fields.sql`

Click **Run** ✅

#### Migration 003: Remove OpenAI Message ID

Copy and paste the **entire contents** of `supabase/migrations/003_remove_openai_message_id.sql`

Click **Run** ✅

#### Migration 004: Add Provider to Threads

Copy and paste the **entire contents** of `supabase/migrations/004_add_provider_to_threads.sql`

Click **Run** ✅

#### Migration 005: Enable pgvector

Copy and paste the **entire contents** of `supabase/migrations/005_enable_pgvector.sql`

```sql
-- Enable pgvector extension for vector embeddings
CREATE EXTENSION IF NOT EXISTS vector;
```

Click **Run** ✅

**Verify pgvector is enabled:**
```sql
SELECT extname FROM pg_extension WHERE extname = 'vector';
```

You should see "vector" in the results.

#### Migration 006: Documents and Chunks Tables

Copy and paste the **entire contents** of `supabase/migrations/006_documents_and_chunks.sql`

Click **Run** ✅

### Step 4: Verify Database Schema

Run this verification query in SQL Editor:

```sql
-- Check all tables exist
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

You should see:
- ✅ chunks
- ✅ documents
- ✅ messages
- ✅ threads

---

## Part 3: Create Storage Bucket

### Step 5: Create 'documents' Bucket

1. In Supabase Dashboard, go to **Storage** in left sidebar
2. Click **New bucket**
3. Configure:
   - **Name:** `documents`
   - **Public bucket:** ❌ Unchecked (keep private)
   - **File size limit:** 50 MB
   - **Allowed MIME types:** Leave empty (allow all)
4. Click **Create bucket**

### Step 6: Configure Storage RLS Policies

**Important:** Use the SQL Editor to create storage policies (the Storage UI form can have syntax issues).

1. Go to **SQL Editor** in the left sidebar
2. Click **New query**
3. Copy and paste this **entire block**:

```sql
-- Storage policies for documents bucket

-- Policy 1: Users can upload their own documents
CREATE POLICY "Users can upload their own documents"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'documents' AND
    (storage.foldername(name))[1] = auth.uid()::text
);

-- Policy 2: Users can read their own documents
CREATE POLICY "Users can read their own documents"
ON storage.objects FOR SELECT
TO authenticated
USING (
    bucket_id = 'documents' AND
    (storage.foldername(name))[1] = auth.uid()::text
);

-- Policy 3: Users can delete their own documents
CREATE POLICY "Users can delete their own documents"
ON storage.objects FOR DELETE
TO authenticated
USING (
    bucket_id = 'documents' AND
    (storage.foldername(name))[1] = auth.uid()::text
);
```

4. Click **Run**

### Step 7: Verify Storage Setup

1. Go to **Storage** > `documents` bucket
2. Under **Policies** tab, verify all 3 policies show green checkmarks

---

## Part 4: Create Test User

### Step 8: Create Test Account

1. In Supabase Dashboard, go to **Authentication** > **Users**
2. Click **Add user** > **Create new user**
3. Fill in:
   - **Email:** test@test.com
   - **Password:** 123456
   - **Auto Confirm User:** ✅ Checked
4. Click **Create user**

---

## Part 5: Update Backend Configuration

### Step 9: Update Environment Variables

Edit `backend/.env` file with your **new** project credentials:

```env
# Supabase - NEW PROJECT CREDENTIALS
SUPABASE_URL=https://[new-project-id].supabase.co
SUPABASE_ANON_KEY=[new-anon-key]
SUPABASE_SERVICE_ROLE_KEY=[new-service-role-key]

# OpenAI (unchanged)
OPENAI_API_KEY=sk-...

# Provider defaults (unchanged)
DEFAULT_PROVIDER=openai
DEFAULT_MODEL=gpt-4o-mini
DEFAULT_BASE_URL=https://api.openai.com/v1

# LangSmith (optional - unchanged if you have it)
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=default
LANGSMITH_TRACING=true

# Server (unchanged)
PORT=8000
CORS_ORIGINS=http://localhost:5173

# Document Processing (unchanged)
EMBEDDING_MODEL=text-embedding-3-small
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_FILE_SIZE_MB=10
SUPPORTED_FILE_TYPES=[".txt", ".pdf", ".docx", ".html", ".md"]
```

### Step 10: Update Frontend Configuration

Edit `frontend/.env` file:

```env
# Supabase - NEW PROJECT CREDENTIALS
VITE_SUPABASE_URL=https://[new-project-id].supabase.co
VITE_SUPABASE_ANON_KEY=[new-anon-key]
```

---

## Part 6: Test the Migration

### Step 11: Restart Servers

**Backend:**
```bash
cd backend
# Make sure venv is activated
source venv/Scripts/activate  # Windows Git Bash
# or
venv\Scripts\activate  # Windows CMD

# Restart server
uvicorn main:app --reload
```

**Frontend:**
```bash
cd frontend
npm run dev
```

### Step 12: Test Authentication

1. Open browser to http://localhost:5173
2. Try logging in with test@test.com / 123456
3. Verify you're redirected to /chat
4. Check browser console for errors

### Step 13: Test Chat Functionality

1. Create a new thread
2. Send a message
3. Verify streaming response works
4. Verify message appears in chat history
5. Refresh page - messages should persist

### Step 14: Verify Database (Optional)

Go to Supabase Dashboard > **Table Editor**:

1. Check **threads** table - should have 1 row
2. Check **messages** table - should have 2 rows (user + assistant)
3. All data should be associated with your test user

### Step 15: Test Vector Extension (Once ingestion is complete)

After you complete the ingestion implementation, verify pgvector works:

```sql
-- In Supabase SQL Editor
-- This should work without errors in the new region
SELECT id, content, embedding <=> '[0.1, 0.2, ...]'::vector AS similarity
FROM chunks
LIMIT 1;
```

---

## Part 7: Cleanup

### Step 16: Archive Old Project (Optional)

Once you've verified everything works in the new project:

1. Go to your **old** Supabase project
2. Project Settings > General
3. **Do NOT delete yet** - keep as backup for 1-2 weeks
4. After confirming new project works perfectly, you can delete the old one

---

## Troubleshooting

### "Extension vector does not exist"
- Make sure you ran Migration 005 in the new project
- Verify region supports pgvector (check project region in Settings)

### "Cannot connect to Supabase"
- Double-check `.env` files have correct URL and keys
- Ensure no typos in environment variables
- Restart backend server after changing .env

### "Authentication failed"
- Verify test user exists in new project
- Check SUPABASE_ANON_KEY matches new project
- Clear browser localStorage and try again

### "RLS policy violation"
- Verify all RLS policies were created correctly
- Check user is authenticated (JWT token valid)
- Review policy SQL for typos

---

## Migration Checklist

Use this to track your progress:

- [ ] Created new Supabase project in supported region
- [ ] Copied new project URL, anon key, service_role key
- [ ] Applied migration 001 (threads, messages)
- [ ] Applied migration 002 (remove assistants fields)
- [ ] Applied migration 003 (remove message IDs)
- [ ] Applied migration 004 (add provider to threads)
- [ ] Applied migration 005 (enable pgvector) ✅ **Critical**
- [ ] Applied migration 006 (documents, chunks) ✅ **Critical**
- [ ] Verified pgvector extension is enabled
- [ ] Created 'documents' storage bucket
- [ ] Added all 3 storage RLS policies
- [ ] Created test user (test@test.com)
- [ ] Updated `backend/.env` with new credentials
- [ ] Updated `frontend/.env` with new credentials
- [ ] Restarted backend server
- [ ] Restarted frontend dev server
- [ ] Tested login with test user
- [ ] Tested chat functionality
- [ ] Verified data in database tables
- [ ] Kept old project as backup (don't delete yet)

---

## Estimated Time

- Project creation: 5 minutes
- Database migrations: 10 minutes
- Storage setup: 5 minutes
- Configuration update: 5 minutes
- Testing: 10 minutes

**Total: ~35 minutes**

---

## Notes

- The old project data will NOT be migrated - you're starting fresh
- This is acceptable since you're in development (no production data)
- All your code changes are preserved - only the database backend changes
- After migration, you can continue with the ingestion router implementation

## Next Steps After Migration

Once migration is complete and tested:
1. Continue with Phase 3: Create ingestion router (`backend/routers/ingestion.py`)
2. Phase 4: Frontend integration (add routes, navigation)
3. End-to-end testing of document upload and embedding

---

**Good luck with the migration! Take your time and check off each step.**
