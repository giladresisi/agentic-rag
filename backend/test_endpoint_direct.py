"""Test the FastAPI endpoint directly with detailed error output."""
from fastapi.testclient import TestClient
from main import app
from services.supabase_service import get_supabase

# Test credentials
TEST_EMAIL = "test@test.com"
TEST_PASSWORD = "123456"

def test():
    print("=== Testing FastAPI Endpoint Directly ===\n")

    # Get auth token
    supabase = get_supabase()
    response = supabase.auth.sign_in_with_password({
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    token = response.session.access_token
    print(f"[OK] Got auth token\n")

    # Create test client
    client = TestClient(app)

    # Test the endpoint
    print("Testing GET /chat/threads...\n")
    try:
        response = client.get(
            "/chat/threads",
            headers={"Authorization": f"Bearer {token}"}
        )

        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")

        if response.status_code == 200:
            print(f"\n[OK] Success! Got {len(response.json())} threads")
            for thread in response.json()[:3]:  # Show first 3
                print(f"  - {thread['title']} ({thread['id']})")
        else:
            print(f"\n[ERROR] Request failed!")
            print(f"Response text: {response.text}")

            # Try to get more details from the response
            try:
                error_detail = response.json()
                print(f"Error detail: {error_detail}")
            except:
                pass

    except Exception as e:
        print(f"\n[ERROR] Exception occurred: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test()
