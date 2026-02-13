"""Detailed diagnostic with raw query output."""
from dotenv import load_dotenv
from services.supabase_service import get_supabase_admin
import os

load_dotenv()

def detailed_check():
    print("=" * 60)
    print("DETAILED DIAGNOSTIC")
    print("=" * 60)

    # Show environment
    print("\nEnvironment:")
    print(f"  SUPABASE_URL: {os.getenv('SUPABASE_URL')}")
    print(f"  Project ID: {os.getenv('SUPABASE_URL', '').split('//')[1].split('.')[0] if os.getenv('SUPABASE_URL') else 'N/A'}")

    supabase = get_supabase_admin()

    # Authenticate
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": "test@test.com",
            "password": "123456"
        })
        user_id = auth_response.user.id
        print(f"\n[OK] Authenticated")
        print(f"  User ID: {user_id}")
    except Exception as e:
        print(f"\n[ERROR] Auth failed: {e}")
        return

    # Query documents with detailed output
    print("\n" + "-" * 60)
    print("Querying documents table...")
    print("-" * 60)

    try:
        # Raw query without filters
        all_docs = supabase.table("documents").select("*").execute()
        print(f"\nTotal documents in table (all users): {len(all_docs.data)}")

        if all_docs.data:
            print("\nAll documents:")
            for doc in all_docs.data:
                print(f"  - {doc['filename']}")
                print(f"    ID: {doc['id']}")
                print(f"    User: {doc['user_id']}")
                print(f"    Status: {doc['status']}")
                print(f"    Chunks: {doc.get('chunk_count', 0)}")
                print()

        # Query for specific user
        user_docs = supabase.table("documents").select("*").eq("user_id", user_id).execute()
        print(f"Documents for user {user_id}: {len(user_docs.data)}")

        if user_docs.data:
            for doc in user_docs.data:
                print(f"  - {doc['filename']} (status: {doc['status']}, chunks: {doc.get('chunk_count', 0)})")

    except Exception as e:
        print(f"[ERROR] Query failed: {e}")
        import traceback
        traceback.print_exc()

    # Query chunks
    print("\n" + "-" * 60)
    print("Querying chunks table...")
    print("-" * 60)

    try:
        all_chunks = supabase.table("chunks").select("id, document_id, user_id").execute()
        print(f"\nTotal chunks (all users): {len(all_chunks.data)}")

        if all_chunks.data:
            # Group by user
            from collections import defaultdict
            by_user = defaultdict(int)
            for chunk in all_chunks.data:
                by_user[chunk['user_id']] += 1

            print("\nChunks by user:")
            for uid, count in by_user.items():
                print(f"  {uid}: {count} chunks")

        user_chunks = supabase.table("chunks").select("*").eq("user_id", user_id).execute()
        print(f"\nChunks for test user: {len(user_chunks.data)}")

    except Exception as e:
        print(f"[ERROR] Chunks query failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    detailed_check()
