# Apply Database Migrations

To apply the pending migrations, you need to run the SQL files in your Supabase dashboard:

## Step 1: Apply Migration 002 (Remove openai_thread_id)

1. Go to your Supabase dashboard: https://app.supabase.com
2. Navigate to: **SQL Editor**
3. Copy and paste the contents of `supabase/migrations/002_remove_assistants_api_fields.sql`:

```sql
-- Remove Assistants API specific fields

-- Drop openai_thread_id column from threads table
ALTER TABLE threads DROP COLUMN IF EXISTS openai_thread_id;
```

4. Click **Run** to execute

## Step 2: Apply Migration 003 (Remove openai_message_id)

1. In the SQL Editor, copy and paste the contents of `supabase/migrations/003_remove_openai_message_id.sql`:

```sql
-- Remove remaining Assistants API field from messages table
ALTER TABLE messages DROP COLUMN IF EXISTS openai_message_id;
```

2. Click **Run** to execute

## Verification

After applying both migrations, verify the columns are removed:

```sql
-- Check threads table schema
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'threads';

-- Check messages table schema
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'messages';
```

You should NOT see:
- `openai_thread_id` in threads table
- `openai_message_id` in messages table

## Complete!

Once migrations are applied, restart your backend server:

```bash
cd backend
uvicorn main:app --reload
```

The backend should now use the Responses API with vector store support (if OPENAI_VECTOR_STORE_ID is configured).
