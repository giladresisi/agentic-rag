# Apply Document Ingestion Migrations

Follow these steps to set up the database and storage for document ingestion.

## Step 1: Enable pgvector Extension

1. Go to your Supabase dashboard: https://app.supabase.com
2. Navigate to: **SQL Editor**
3. Copy and paste the contents of `supabase/migrations/005_enable_pgvector.sql`:

```sql
-- Enable pgvector extension for vector embeddings
CREATE EXTENSION IF NOT EXISTS vector;
```

4. Click **Run** to execute

## Step 2: Create Documents and Chunks Tables

1. In the SQL Editor, copy and paste the **entire contents** of `supabase/migrations/006_documents_and_chunks.sql`
2. Click **Run** to execute

This will create:
- `documents` table with status tracking
- `chunks` table with vector(1536) embeddings
- Indexes for performance (including IVFFlat for vector search)
- RLS policies for both tables
- Auto-update trigger for `updated_at` timestamp

## Step 3: Create Storage Bucket

**Important:** Storage buckets cannot be created via SQL. Follow these steps in the Supabase Dashboard:

1. In your Supabase dashboard, go to **Storage** in the left sidebar
2. Click **New bucket**
3. Configure the bucket:
   - **Name:** `documents`
   - **Public bucket:** ❌ Unchecked (keep it private)
   - **File size limit:** 50 MB
   - **Allowed MIME types:** Leave empty (allow all)
4. Click **Create bucket**

## Step 4: Configure Storage Policies

After creating the bucket, set up RLS policies using the SQL Editor:

1. Go to **SQL Editor** in the left sidebar
2. Click **New query**
3. Copy and paste this **entire block** and click **Run**:

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

## Verification

After setup, verify everything is working:

### Verify Tables
```sql
-- Check documents table exists
SELECT * FROM documents LIMIT 0;

-- Check chunks table exists
SELECT * FROM chunks LIMIT 0;

-- Verify pgvector is enabled
SELECT extname FROM pg_extension WHERE extname = 'vector';
```

### Verify Storage
1. Go to **Storage** > `documents` bucket
2. Verify all 3 policies are active (green checkmarks)
3. Try uploading a test file (will test via frontend later)

## Complete!

Once migrations and storage are set up:
- ✅ pgvector extension enabled
- ✅ documents table created with RLS
- ✅ chunks table created with vector embeddings and IVFFlat index
- ✅ Storage bucket 'documents' created with RLS policies

The backend ingestion API can now process documents and store embeddings!
