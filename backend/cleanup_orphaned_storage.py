"""
Cleanup orphaned storage files (files without database records).
"""
from dotenv import load_dotenv
from services.supabase_service import get_supabase_admin

load_dotenv()

def cleanup_orphaned_files():
    """Delete storage files that don't have corresponding database records."""
    print("=" * 60)
    print("CLEANUP ORPHANED STORAGE FILES")
    print("=" * 60)

    supabase = get_supabase_admin()

    # Get all storage paths
    storage_files = supabase.storage.from_("documents").list()
    all_storage_paths = []

    for folder in storage_files:
        folder_name = folder['name']
        files_in_folder = supabase.storage.from_("documents").list(folder_name)
        for file in files_in_folder:
            path = f"{folder_name}/{file['name']}"
            all_storage_paths.append(path)

    print(f"Found {len(all_storage_paths)} files in storage")

    # Get all database paths
    db_docs = supabase.table("documents").select("storage_path").execute()
    db_paths = set(doc['storage_path'] for doc in db_docs.data)

    print(f"Found {len(db_paths)} files in database")

    # Find orphaned files
    orphaned = [path for path in all_storage_paths if path not in db_paths]

    if not orphaned:
        print("\n[PASS] No orphaned files to clean up")
        return

    print(f"\nFound {len(orphaned)} orphaned files:")
    for path in orphaned:
        print(f"  - {path}")

    # Delete orphaned files
    print("\nDeleting orphaned files...")
    try:
        result = supabase.storage.from_("documents").remove(orphaned)
        print(f"[PASS] Deleted {len(orphaned)} orphaned files")
    except Exception as e:
        print(f"[FAIL] Error deleting files: {e}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    cleanup_orphaned_files()
