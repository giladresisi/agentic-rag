"""Debug streaming response to see what's happening."""
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

TEST_EMAIL = os.getenv("TEST_EMAIL")
TEST_PASSWORD = os.getenv("TEST_PASSWORD")
BASE_URL = "http://localhost:8000"


def main():
    print("\n=== DEBUG STREAMING TEST ===\n")

    # Authenticate
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code != 200:
        print(f"[FAIL] Auth: {response.status_code} - {response.text}")
        return

    token = response.json()["access_token"]
    print(f"[OK] Authenticated\n")

    # Create thread
    response = requests.post(
        f"{BASE_URL}/chat/threads",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Debug Test"}
    )
    thread_id = response.json()["id"]
    print(f"[OK] Thread: {thread_id}\n")

    # Send simple query
    query = "What P1 incidents are in the database?"

    print(f"Query: {query}\n")
    print("Streaming response:\n" + "="*70)

    response = requests.post(
        f"{BASE_URL}/chat/threads/{thread_id}/messages",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "content": query,
            "provider": "openai",
            "model": "gpt-4o-mini"
        },
        stream=True
    )

    print(f"Response Status: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}\n")

    line_count = 0
    for line in response.iter_lines():
        if line:
            line_count += 1
            line_str = line.decode('utf-8')
            print(f"[Line {line_count}] {line_str[:200]}")  # First 200 chars

            if line_str.startswith('data: '):
                data = line_str[6:]
                if data.strip() == '[DONE]':
                    print("[Stream completed]")
                    break

    print("="*70)
    print(f"\nTotal lines received: {line_count}")


if __name__ == "__main__":
    main()
