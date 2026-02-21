"""
MANUAL TEST - Requires a live server.
  Run: cd backend && uvicorn main:app --reload
  Then: python tests/manual/test_detailed_error.py

Test to see detailed error from backend.
"""
import sys
from pathlib import Path
# Make backend modules importable when run directly
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # backend/
sys.path.insert(0, str(Path(__file__).parent.parent))         # backend/tests/

import os
from dotenv import load_dotenv
import requests
from services.supabase_service import get_supabase

load_dotenv()
TEST_EMAIL = os.getenv("TEST_EMAIL")
TEST_PASSWORD = os.getenv("TEST_PASSWORD")


def test():
    # Get auth token
    supabase = get_supabase()
    response = supabase.auth.sign_in_with_password({
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    token = response.session.access_token

    print(f"Testing /chat/threads endpoint...")

    # Test with detailed error handling
    resp = requests.get(
        "http://localhost:8000/chat/threads",
        headers={"Authorization": f"Bearer {token}"}
    )

    print(f"\nStatus Code: {resp.status_code}")
    print(f"\nHeaders: {dict(resp.headers)}")
    print(f"\nRaw Response Text:\n{resp.text}")

    if resp.status_code != 200:
        print("\n[ERROR] API request failed!")
        print("Check the backend server console for the full Python traceback.")
    else:
        print("\n[OK] API request successful!")
        print(f"Threads: {resp.json()}")

if __name__ == "__main__":
    test()
