"""Delete all documents, chunks, storage files, threads, and messages for the test user.

Reads TEST_EMAIL and TEST_PASSWORD from backend/.env.

Usage (from backend/ directory):
    python -m scripts.reset_user_data
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_service import get_supabase, get_supabase_admin

TEST_EMAIL = os.getenv("TEST_EMAIL")
TEST_PASSWORD = os.getenv("TEST_PASSWORD")


def main():
    if not TEST_EMAIL or not TEST_PASSWORD:
        print("ERROR: TEST_EMAIL and TEST_PASSWORD must be set in backend/.env")
        sys.exit(1)

    supabase = get_supabase()
    admin = get_supabase_admin()

    # Sign in to get user_id
    auth = supabase.auth.sign_in_with_password({"email": TEST_EMAIL, "password": TEST_PASSWORD})
    user_id = auth.user.id
    print(f"Signed in as {TEST_EMAIL} (user_id={user_id})")

    # Delete threads (messages cascade via ON DELETE CASCADE)
    result = admin.table("threads").delete().eq("user_id", user_id).execute()
    print(f"Deleted {len(result.data)} thread(s) (messages cascaded)")

    # Get storage paths before deleting documents
    docs = admin.table("documents").select("storage_path").eq("user_id", user_id).execute()
    storage_paths = [d["storage_path"] for d in docs.data if d.get("storage_path")]

    # Delete documents (chunks cascade via ON DELETE CASCADE)
    result = admin.table("documents").delete().eq("user_id", user_id).execute()
    print(f"Deleted {len(result.data)} document(s) (chunks cascaded)")

    # Delete storage files
    if storage_paths:
        admin.storage.from_("documents").remove(storage_paths)
        print(f"Deleted {len(storage_paths)} file(s) from storage")

    # Clean up any orphaned files in the user's storage folder
    try:
        orphans = admin.storage.from_("documents").list(user_id)
        if orphans:
            orphan_paths = [f"{user_id}/{f['name']}" for f in orphans]
            admin.storage.from_("documents").remove(orphan_paths)
            print(f"Deleted {len(orphan_paths)} orphaned file(s) from storage")
    except Exception:
        pass  # folder may not exist

    print("Done.")


if __name__ == "__main__":
    main()
