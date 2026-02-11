"""Direct test of list_threads function."""
import asyncio
from routers.chat import list_threads
from services.supabase_service import get_supabase

async def test_list_threads_direct():
    """Test the list_threads function directly."""
    # Get test user
    supabase = get_supabase()

    # Get token
    response = supabase.auth.sign_in_with_password({
        "email": "test@test.com",
        "password": "123456"
    })

    user_id = response.user.id
    print(f"User ID: {user_id}")

    # Mock the current_user dict that would come from auth middleware
    current_user = {
        "id": user_id,
        "email": response.user.email,
        "token": response.session.access_token
    }

    # Call list_threads directly
    try:
        result = await list_threads(current_user=current_user)
        print(f"\nSuccess! Got {len(result)} threads")
        for thread in result[:3]:
            print(f"  - {thread.title} ({thread.id})")
    except Exception as e:
        print(f"\nError: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_list_threads_direct())
