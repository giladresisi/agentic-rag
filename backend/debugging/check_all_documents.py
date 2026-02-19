"""Check all documents in the database."""
import _setup_path  # noqa - sets up Python path for imports
from dotenv import load_dotenv
from services.supabase_service import get_supabase_admin

load_dotenv()

def check_all_docs():
    supabase = get_supabase_admin()

    # Get all documents
    response = supabase.table("documents").select("*").execute()

    print("=" * 60)
    print("ALL DOCUMENTS IN DATABASE")
    print("=" * 60)

    if response.data:
        print(f"\nFound {len(response.data)} total document(s):\n")
        for doc in response.data:
            print(f"Filename: {doc['filename']}")
            print(f"  User ID: {doc['user_id']}")
            print(f"  Status: {doc['status']}")
            print(f"  Chunk Count: {doc['chunk_count']}")
            print(f"  Created: {doc['created_at']}")
            print()
    else:
        print("\n[WARN] No documents found in the entire database!")
        print("This means the ingestion pipeline has never successfully completed.")

    # Get all chunks
    chunks_response = supabase.table("chunks").select("id, user_id, document_id").execute()
    print(f"Total chunks in database: {len(chunks_response.data)}")

if __name__ == "__main__":
    check_all_docs()
