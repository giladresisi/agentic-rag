"""Test what similarity different queries get."""
import asyncio
from dotenv import load_dotenv
from services.supabase_service import get_supabase_admin
from services.retrieval_service import retrieval_service

load_dotenv()

async def test():
    supabase = get_supabase_admin()
    auth_response = supabase.auth.sign_in_with_password({
        "email": "test@...",
        "password": "***"
    })
    user_id = auth_response.user.id

    queries = [
        "document content",
        "document overview",
        "test document",
        "markdown",
        "section",
        "Tell me about my uploaded document",
    ]

    print("=" * 60)
    print("QUERY SIMILARITY COMPARISON")
    print("=" * 60)

    for query in queries:
        try:
            results = await retrieval_service.retrieve_relevant_chunks(
                query=query,
                user_id=user_id,
                similarity_threshold=0.0,  # No threshold to see actual score
                limit=1
            )

            if results:
                similarity = results[0]['similarity']
                print(f"\nQuery: '{query}'")
                print(f"  Similarity: {similarity:.3f}")
                print(f"  Pass 0.4? {'YES' if similarity >= 0.4 else 'NO'}")
            else:
                print(f"\nQuery: '{query}'")
                print(f"  No results (unexpected)")

        except Exception as e:
            print(f"\nQuery: '{query}'")
            print(f"  Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
