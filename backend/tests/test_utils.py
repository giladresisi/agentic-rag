"""
Utility functions for testing.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add backend directory to Python path so tests can import backend modules
# This allows tests to be run from the tests directory
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from services.supabase_service import get_supabase_admin

# Load environment variables from .env file
# This ensures TEST_EMAIL and TEST_PASSWORD are available from .env
load_dotenv()

# Test credentials configuration
# These are loaded from .env file (TEST_EMAIL, TEST_PASSWORD)
# For public repositories, keep actual credentials in .env (gitignored)
TEST_EMAIL = os.getenv("TEST_EMAIL", "test@...")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "***")


def cleanup_test_documents_and_storage(user_id: str, doc_ids: list | None = None, cleanup_orphaned: bool = True):
    """
    Clean up test documents from database AND storage.

    Args:
        user_id: User ID (required for storage orphan cleanup)
        doc_ids: Specific document IDs to delete. When provided, only those
                 documents are removed and orphaned cleanup is skipped — this
                 is the safe mode that avoids touching unrelated user data
                 (e.g. eval postmortem files). When None, ALL documents for
                 the user are deleted (legacy behaviour — avoid in new tests).
        cleanup_orphaned: When True and doc_ids is None, also delete storage
                          files that have no matching DB record.
    """
    supabase = get_supabase_admin()

    try:
        if doc_ids is not None:
            # Targeted cleanup: only the documents this test created.
            if not doc_ids:
                return  # Nothing to clean up

            # Step 1: Fetch storage paths for the specific docs
            docs_response = supabase.table("documents")\
                .select("storage_path")\
                .in_("id", doc_ids)\
                .execute()

            storage_paths_from_db = [doc['storage_path'] for doc in docs_response.data if doc.get('storage_path')]

            # Step 2: Delete from database (chunks cascade automatically)
            supabase.table("documents").delete().in_("id", doc_ids).execute()
        else:
            # Legacy full-user cleanup (use only when no doc_ids are available).
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

        # Step 4: Clean up orphaned files (files in storage without DB records).
        # Only applies to full-user cleanup; targeted (doc_ids) cleanup never
        # touches files outside the explicitly requested set.
        if doc_ids is None and cleanup_orphaned:
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
