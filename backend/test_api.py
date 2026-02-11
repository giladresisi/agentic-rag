"""
Quick diagnostic script to test the threads API endpoint.
"""
import requests
from services.supabase_service import get_supabase

# Test credentials from CLAUDE.md
TEST_EMAIL = "test@test.com"
TEST_PASSWORD = "123456"

def test_auth():
    """Test authentication and get token."""
    supabase = get_supabase()

    try:
        response = supabase.auth.sign_in_with_password({
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })

        token = response.session.access_token
        user_id = response.user.id

        print(f"[OK] Authentication successful")
        print(f"  User ID: {user_id}")
        print(f"  Token: {token[:20]}...")

        return token, user_id
    except Exception as e:
        print(f"[ERROR] Authentication failed: {e}")
        return None, None


def test_threads_api(token):
    """Test the threads API endpoint."""
    url = "http://localhost:8000/chat/threads"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(url, headers=headers)
        print(f"\n[INFO] API response status: {response.status_code}")
        print(f"  Response text: {response.text[:500]}")  # First 500 chars

        if response.status_code == 200:
            return response.json()
        else:
            print(f"[ERROR] API returned error status {response.status_code}")
            return None
    except Exception as e:
        print(f"\n[ERROR] API request failed: {e}")
        return None


def test_database_direct(user_id):
    """Test direct database query."""
    supabase = get_supabase()

    try:
        response = supabase.table("threads").select("*").eq("user_id", user_id).execute()
        print(f"\n[OK] Database query successful")
        print(f"  Found {len(response.data)} threads")
        for thread in response.data:
            print(f"    - {thread['title']} (ID: {thread['id']})")
        return response.data
    except Exception as e:
        print(f"\n[ERROR] Database query failed: {e}")
        return None


if __name__ == "__main__":
    print("=== Testing Threads API ===\n")

    # Test authentication
    token, user_id = test_auth()

    if token and user_id:
        # Test API endpoint
        test_threads_api(token)

        # Test direct database query
        test_database_direct(user_id)
    else:
        print("\nCannot proceed without authentication.")
