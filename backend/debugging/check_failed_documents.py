"""Check for failed document processing."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _setup_path  # noqa - sets up Python path for imports
from dotenv import load_dotenv
from services.supabase_service import get_supabase_admin

load_dotenv()

def check_failed():
    supabase = get_supabase_admin()

    # Check for failed documents
    response = supabase.table("documents").select("*").eq("status", "failed").execute()

    print("=" * 60)
    print("FAILED DOCUMENTS CHECK")
    print("=" * 60)

    if response.data:
        print(f"\nFound {len(response.data)} failed document(s):\n")
        for doc in response.data:
            print(f"Filename: {doc['filename']}")
            print(f"  User ID: {doc['user_id']}")
            print(f"  Error: {doc.get('error_message', 'No error message')}")
            print(f"  Created: {doc['created_at']}")
            print()
    else:
        print("\nNo failed documents found.")
        print("Checking for processing documents...")

        # Check for stuck "processing" documents
        processing = supabase.table("documents").select("*").eq("status", "processing").execute()

        if processing.data:
            print(f"\nFound {len(processing.data)} document(s) stuck in 'processing' state:")
            for doc in processing.data:
                print(f"  - {doc['filename']} (created: {doc['created_at']})")
            print("\nThese may have failed without updating status.")
        else:
            print("\nNo processing documents found either.")
            print("The upload may have failed before creating a document record.")

if __name__ == "__main__":
    check_failed()
