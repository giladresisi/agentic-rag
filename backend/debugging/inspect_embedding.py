"""Inspect the actual embedding data in the database."""
import _setup_path  # noqa - sets up Python path for imports
from dotenv import load_dotenv
from services.supabase_service import get_supabase_admin
import json

load_dotenv()

def inspect():
    supabase = get_supabase_admin()

    # Get chunk with embedding
    response = supabase.table("chunks").select("*").limit(1).execute()

    if not response.data:
        print("No chunks found")
        return

    chunk = response.data[0]
    embedding = chunk.get('embedding')

    print("=" * 60)
    print("EMBEDDING INSPECTION")
    print("=" * 60)

    print(f"\nChunk ID: {chunk['id']}")
    print(f"Document ID: {chunk['document_id']}")
    print(f"Content (first 100 chars): {chunk['content'][:100]}...")

    print(f"\nEmbedding Type: {type(embedding)}")
    print(f"Embedding Length: {len(embedding) if embedding else 'None'}")

    if embedding:
        # Check if it's already a list or needs parsing
        if isinstance(embedding, str):
            print("  WARNING: Embedding is stored as string!")
            try:
                parsed = json.loads(embedding)
                print(f"  Parsed length: {len(parsed)}")
                print(f"  First 5 values: {parsed[:5]}")
            except:
                print("  Failed to parse as JSON")
        elif isinstance(embedding, list):
            print("  Embedding is a list (correct)")
            print(f"  First 5 values: {embedding[:5]}")
            print(f"  Last 5 values: {embedding[-5:]}")

            # Check if values look like floats
            sample = embedding[:10]
            print(f"  Sample values types: {[type(v) for v in sample]}")

    # Check embedding_dimensions field
    print(f"\nEmbedding Dimensions (stored field): {chunk.get('embedding_dimensions', 'Not set')}")

if __name__ == "__main__":
    inspect()
