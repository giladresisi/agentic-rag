# Supabase Storage Setup for Document Ingestion

This document describes how to create and configure the Supabase Storage bucket for document uploads.

## Manual Setup Required

Supabase Storage buckets cannot be created via SQL migrations. Follow these steps in the Supabase Dashboard:

### 1. Create the Storage Bucket

1. Navigate to your Supabase project dashboard
2. Go to **Storage** in the left sidebar
3. Click **New bucket**
4. Configure the bucket:
   - **Name:** `documents`
   - **Public bucket:** Unchecked (private)
   - **File size limit:** 50 MB (or adjust as needed)
   - **Allowed MIME types:** Leave empty to allow all document types

### 2. Configure Storage Policies

After creating the bucket, set up Row-Level Security policies:

1. In the Storage section, click on the `documents` bucket
2. Go to **Policies** tab
3. Add the following policies:

#### Policy 1: Allow authenticated users to upload files
```sql
-- Policy name: Users can upload their own documents
-- Operation: INSERT
-- Target roles: authenticated

CREATE POLICY "Users can upload their own documents"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'documents' AND
    auth.uid()::text = (storage.foldername(name))[1]
);
```

#### Policy 2: Allow users to read their own files
```sql
-- Policy name: Users can read their own documents
-- Operation: SELECT
-- Target roles: authenticated

CREATE POLICY "Users can read their own documents"
ON storage.objects FOR SELECT
TO authenticated
USING (
    bucket_id = 'documents' AND
    auth.uid()::text = (storage.foldername(name))[1]
);
```

#### Policy 3: Allow users to delete their own files
```sql
-- Policy name: Users can delete their own documents
-- Operation: DELETE
-- Target roles: authenticated

CREATE POLICY "Users can delete their own documents"
ON storage.objects FOR DELETE
TO authenticated
USING (
    bucket_id = 'documents' AND
    auth.uid()::text = (storage.foldername(name))[1]
);
```

### Storage Path Convention

Files should be stored using the following path pattern:
```
{user_id}/{document_id}/{filename}
```

Example:
```
550e8400-e29b-41d4-a716-446655440000/a1b2c3d4-e5f6-7890-abcd-ef1234567890/report.pdf
```

This ensures:
- Each user's files are isolated in their own folder
- RLS policies can enforce user-level access control
- File paths are unique and predictable
- Easy cleanup when documents are deleted

### Validation

After setup, verify the bucket is working:

1. Check the bucket exists in the Storage UI
2. Verify all three policies are active
3. Test upload with the test user (test@...)
4. Confirm the file appears in the Storage browser
5. Verify access restrictions (users cannot see other users' files)

## Backend Integration

The backend will use these environment variables to interact with Storage:

```env
SUPABASE_URL=your-project-url
SUPABASE_SERVICE_KEY=your-service-role-key
```

The service key allows the backend to bypass RLS and manage files on behalf of users.
