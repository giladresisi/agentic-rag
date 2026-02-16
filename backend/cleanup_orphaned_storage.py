"""
Cleanup orphaned storage files (files without database records).

Usage:
    python cleanup_orphaned_storage.py            # Interactive mode (asks for confirmation)
    python cleanup_orphaned_storage.py --yes      # Auto-confirm deletion
    python cleanup_orphaned_storage.py --dry-run  # Show what would be deleted
"""
import sys
from dotenv import load_dotenv
from services.supabase_service import get_supabase_admin

load_dotenv()

def cleanup_orphaned_files(auto_confirm=False, dry_run=False):
    """Delete storage files that don't have corresponding database records."""
    print("=" * 60)
    print("CLEANUP ORPHANED STORAGE FILES")
    print("=" * 60)

    supabase = get_supabase_admin()

    # Get all storage paths
    print("\nScanning storage...")
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
    print("Checking database...")
    db_docs = supabase.table("documents").select("storage_path").execute()
    db_paths = set(doc['storage_path'] for doc in db_docs.data)

    print(f"Found {len(db_paths)} files in database")

    # Find orphaned files
    orphaned = [path for path in all_storage_paths if path not in db_paths]

    if not orphaned:
        print("\n+ No orphaned files to clean up")
        return

    print(f"\nFound {len(orphaned)} orphaned files:")
    for path in orphaned:
        print(f"  - {path}")

    if dry_run:
        print(f"\n[DRY RUN] Would delete {len(orphaned)} files")
        print("Run without --dry-run to actually delete")
        return

    # Confirm deletion
    if not auto_confirm:
        response = input(f"\nDelete {len(orphaned)} orphaned files? (yes/no): ")
        if response.lower() != "yes":
            print("Cancelled.")
            return

    # Delete orphaned files
    print("\nDeleting orphaned files...")
    try:
        result = supabase.storage.from_("documents").remove(orphaned)
        print(f"+ Deleted {len(orphaned)} orphaned files")
    except Exception as e:
        print(f"- Error deleting files: {e}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    auto_confirm = "--yes" in sys.argv
    dry_run = "--dry-run" in sys.argv

    try:
        cleanup_orphaned_files(auto_confirm=auto_confirm, dry_run=dry_run)
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(1)
