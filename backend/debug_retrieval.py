"""Debug the retrieval function."""
import asyncio
from dotenv import load_dotenv
from services.supabase_service import get_supabase_admin
from services.embedding_service import embedding_service

load_dotenv()

async def debug():
    supabase = get_supabase_admin()
    auth_response = supabase.auth.sign_in_with_password({
        "email": "test@test.com",
        "password": "123456"
    })
    user_id = auth_response.user.id

    # Test with both queries
    queries = ["document content", "document overview"]

    for query in queries:
        print(f"\n{'='*60}")
        print(f"Testing: '{query}'")
        print("="*60)

        # Generate embedding
        embeddings = await embedding_service.generate_embeddings([query])
        query_embedding = embeddings[0]

        print(f"Query embedding dimensions: {len(query_embedding)}")
        print(f"First 5 values: {query_embedding[:5]}")

        # Call the RPC function directly
        try:
            response = supabase.rpc(
                'match_chunks_v2',
                {
                    'query_embedding': query_embedding,
                    'match_threshold': 0.0,
                    'match_count': 5,
                    'user_id_filter': user_id,
                    'dimension_filter': len(query_embedding)
                }
            ).execute()

            print(f"\nRPC Response:")
            print(f"  Data count: {len(response.data) if response.data else 0}")

            if response.data:
                for chunk in response.data:
                    print(f"  - Similarity: {chunk['similarity']:.3f}")
                    print(f"    Content: {chunk['content'][:60]}...")
            else:
                print("  No results returned")

        except Exception as e:
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug())
