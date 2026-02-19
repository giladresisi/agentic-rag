"""
Delete all documents for testing purposes.

Usage:
    python delete_all_documents.py --user-id USER_ID
    python delete_all_documents.py --all  # Delete for all users
"""
import _setup_path  # noqa - sets up Python path for imports
import sys
from dotenv import load_dotenv
from services.supabase_service import get_supabase_admin

load_dotenv()


def delete_all_documents(user_id=None):
    """Delete all documents (and their storage files) for testing."""
    supabase = get_supabase_admin()

    # Get documents
    query = supabase.table("documents").select("id, filename, storage_path, user_id")
    if user_id:
        query = query.eq("user_id", user_id)

    docs = query.execute()

    if not docs.data:
        print("No documents found")
        return

    print(f"\nFound {len(docs.data)} documents:")
    for doc in docs.data:
        print(f"  - {doc['filename']}")

    # Confirm
    response = input(f"\nDelete all {len(docs.data)} documents? (yes/no): ")
    if response.lower() != "yes":
        print("Cancelled")
        return

    # Delete each document (this will trigger our delete endpoint logic)
    deleted = 0
    failed = 0

    for doc in docs.data:
        try:
            # Delete from storage first
            try:
                supabase.storage.from_("documents").remove([doc["storage_path"]])
                print(f"  + Deleted storage: {doc['filename']}")
            except Exception as e:
                print(f"  - Storage deletion warning for {doc['filename']}: {e}")

            # Delete chunks (handled by CASCADE in database)
            # Delete document from database
            supabase.table("documents").delete().eq("id", doc["id"]).execute()
            print(f"  + Deleted database record: {doc['filename']}")
            deleted += 1

        except Exception as e:
            print(f"  - Failed to delete {doc['filename']}: {e}")
            failed += 1

    print(f"\nDeletion complete:")
    print(f"  Deleted: {deleted}")
    print(f"  Failed: {failed}")


if __name__ == "__main__":
    if "--all" in sys.argv:
        delete_all_documents()
    elif "--user-id" in sys.argv:
        idx = sys.argv.index("--user-id")
        if idx + 1 < len(sys.argv):
            user_id = sys.argv[idx + 1]
            delete_all_documents(user_id=user_id)
        else:
            print("Error: --user-id requires a value")
            sys.exit(1)
    else:
        print("Usage:")
        print("  python delete_all_documents.py --user-id USER_ID")
        print("  python delete_all_documents.py --all")
        sys.exit(1)
