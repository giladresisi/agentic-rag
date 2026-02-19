"""
Check for orphaned storage files (files in storage without database records).
"""
from dotenv import load_dotenv
from services.supabase_service import get_supabase_admin

load_dotenv()

def check_storage_sync():
    """Check for discrepancies between storage and database."""
    print("=" * 60)
    print("STORAGE SYNC CHECK")
    print("=" * 60)

    supabase = get_supabase_admin()

    # Get all files from storage
    try:
        storage_files = supabase.storage.from_("documents").list()
        print(f"\nStorage folders: {len(storage_files)}")

        total_storage_files = 0
        all_storage_paths = []

        for folder in storage_files:
            folder_name = folder['name']
            files_in_folder = supabase.storage.from_("documents").list(folder_name)
            print(f"  {folder_name}: {len(files_in_folder)} files")
            total_storage_files += len(files_in_folder)

            for file in files_in_folder:
                path = f"{folder_name}/{file['name']}"
                all_storage_paths.append(path)
                print(f"    - {file['name']}")

        print(f"\nTotal storage files: {total_storage_files}")

    except Exception as e:
        print(f"Error listing storage: {e}")
        return

    # Get all documents from database
    try:
        db_docs = supabase.table("documents").select("storage_path, filename").execute()
        print(f"\nDatabase documents: {len(db_docs.data)}")

        db_paths = set(doc['storage_path'] for doc in db_docs.data)

        for doc in db_docs.data:
            print(f"  - {doc['filename']} ({doc['storage_path']})")

    except Exception as e:
        print(f"Error querying database: {e}")
        return

    # Find orphaned files (in storage but not in database)
    orphaned = [path for path in all_storage_paths if path not in db_paths]

    if orphaned:
        print(f"\n[WARN] Found {len(orphaned)} orphaned files in storage:")
        for path in orphaned:
            print(f"  - {path}")
        print("\nThese files have no corresponding database records.")
        print("They were likely created during testing and not cleaned up properly.")
        print("\nTo fix: Delete these files from storage bucket or re-upload them properly.")
    else:
        print("\n[PASS] No orphaned files - storage and database in sync")

    # Find missing files (in database but not in storage)
    storage_paths_set = set(all_storage_paths)
    missing = [doc for doc in db_docs.data if doc['storage_path'] not in storage_paths_set]

    if missing:
        print(f"\n[WARN] Found {len(missing)} database records without storage files:")
        for doc in missing:
            print(f"  - {doc['filename']} (expected at: {doc['storage_path']})")
        print("\nThese records point to files that don't exist in storage.")
    else:
        print("\n[PASS] All database records have corresponding storage files")

    print("\n" + "=" * 60)
    print("CONCLUSION:")
    if orphaned or missing:
        print("Storage and database are OUT OF SYNC")
        if orphaned:
            print(f"- {len(orphaned)} orphaned files in storage")
        if missing:
            print(f"- {len(missing)} missing storage files")
    else:
        print("Storage and database are IN SYNC")
    print("=" * 60)


if __name__ == "__main__":
    check_storage_sync()
