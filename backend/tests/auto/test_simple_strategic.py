"""Simple test for strategic retrieval - incidents database only."""
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

TEST_EMAIL = os.getenv("TEST_EMAIL")
TEST_PASSWORD = os.getenv("TEST_PASSWORD")
BASE_URL = "http://localhost:8000"


def main():
    print("\n=== STRATEGIC RETRIEVAL TEST ===\n")

    # Authenticate
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code != 200:
        print(f"[FAIL] Authentication failed: {response.json()}")
        return

    token = response.json()["access_token"]
    print(f"[OK] Authenticated as {TEST_EMAIL}\n")

    # Create thread
    response = requests.post(
        f"{BASE_URL}/chat/threads",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Strategic Test"}
    )
    if response.status_code not in [200, 201]:
        print(f"[FAIL] Thread creation failed: {response.json()}")
        return

    thread_id = response.json()["id"]
    print(f"[OK] Created thread: {thread_id}\n")

    # Send complex query that should trigger multiple tool calls
    print("="*70)
    print("QUERY: Multi-part incidents database question")
    print("(Should trigger multiple query_deployments_database calls)")
    print("="*70)

    query = """I have two separate questions about production incidents:
    1. What P1 incidents had resolution times over 100 minutes?
    2. Which incidents affected the payment service?

    Please answer both questions thoroughly."""

    print(f"\nSending query...\n")

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

    if response.status_code != 200:
        print(f"[FAIL] Chat request failed: {response.text}")
        return

    print("Response:\n" + "-"*70)

    full_response = ""
    sources = None

    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = line[6:]
                if data.strip() == '[DONE]':
                    break
                try:
                    chunk = json.loads(data)
                    if 'content' in chunk and chunk['content']:
                        print(chunk['content'], end='', flush=True)
                        full_response += chunk['content']
                    if 'sources' in chunk and chunk['sources']:
                        sources = chunk['sources']
                except json.JSONDecodeError as e:
                    pass

    print("\n" + "-"*70)

    if sources:
        print(f"\n[INFO] Sources retrieved: {len(sources)} chunks")

    print(f"\n[INFO] Total response length: {len(full_response)} characters")

    print("\n" + "="*70)
    print("CHECK LANGSMITH DASHBOARD")
    print("="*70)
    print("Look for:")
    print("  - Total tool_calls_count in main trace outputs")
    print("  - Individual tool_calls array showing each call")
    print("  - Child traces for each tool execution")
    print("="*70)


if __name__ == "__main__":
    main()
