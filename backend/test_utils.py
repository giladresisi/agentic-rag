"""
Utility functions for testing.
"""
import os
from services.supabase_service import get_supabase_admin


# Test credentials configuration
# These should be set in .env file or environment variables
# See CLAUDE.md for documentation of test account
TEST_EMAIL = os.getenv("TEST_EMAIL", "test@...")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "***")


def cleanup_test_documents_and_storage(user_id: str, cleanup_orphaned: bool = True):
    """
    Clean up test documents from database AND storage, including orphaned files.

    This prevents orphaned files in storage after tests run.

    Args:
        user_id: User ID whose documents should be cleaned up
        cleanup_orphaned: Also delete orphaned files (files without DB records)
    """
    supabase = get_supabase_admin()

    try:
        # Step 1: Get all documents for this user (to get storage paths)
        docs_response = supabase.table("documents")\
            .select("storage_path")\
            .eq("user_id", user_id)\
            .execute()

        storage_paths_from_db = [doc['storage_path'] for doc in docs_response.data if doc.get('storage_path')]

        # Step 2: Delete from database (chunks cascade automatically)
        supabase.table("documents").delete().eq("user_id", user_id).execute()

        # Step 3: Delete files from storage (both tracked and orphaned)
        deleted_count = 0

        # Delete files that had database records
        if storage_paths_from_db:
            try:
                result = supabase.storage.from_("documents").remove(storage_paths_from_db)
                deleted_count += len(storage_paths_from_db)
                print(f"[CLEANUP] Deleted {len(storage_paths_from_db)} tracked file(s) from storage")
            except Exception as e:
                print(f"[WARN] Storage cleanup error (tracked files): {e}")

        # Step 4: Clean up orphaned files (files in storage without DB records)
        if cleanup_orphaned:
            try:
                # List all files in user's storage folder
                user_folder_files = supabase.storage.from_("documents").list(user_id)

                if user_folder_files:
                    # Build full paths for orphaned files
                    orphaned_paths = [f"{user_id}/{file['name']}" for file in user_folder_files]

                    # Remove orphaned files
                    if orphaned_paths:
                        result = supabase.storage.from_("documents").remove(orphaned_paths)
                        deleted_count += len(orphaned_paths)
                        print(f"[CLEANUP] Deleted {len(orphaned_paths)} orphaned file(s) from storage")

            except Exception as e:
                # Folder might not exist, which is fine
                if "not found" not in str(e).lower():
                    print(f"[WARN] Orphaned files cleanup error: {e}")

        print(f"[CLEANUP] Total cleanup: {deleted_count} file(s) deleted from storage")
        print(f"[CLEANUP] Cleaned up all data for user {user_id}")

    except Exception as e:
        print(f"[WARN] Cleanup error: {e}")
        import traceback
        traceback.print_exc()
