"""
MANUAL TEST - Requires a live server.
  Run: cd backend && uvicorn main:app --reload
  Then: python tests/manual/test_strategic_final.py

Test strategic retrieval with proper SSE format handling.
"""
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

TEST_EMAIL = os.getenv("TEST_EMAIL")
TEST_PASSWORD = os.getenv("TEST_PASSWORD")
BASE_URL = "http://localhost:8000"


def parse_sse_line(line_str):
    """Parse SSE format line."""
    if line_str.startswith('data: '):
        data = line_str[6:].strip()
        if data == '[DONE]':
            return None, True
        try:
            return json.loads(data), False
        except json.JSONDecodeError:
            return None, False
    return None, False


def main():
    print("\n" + "="*80)
    print(" STRATEGIC RETRIEVAL TEST - Incidents Database")
    print("="*80 + "\n")

    # Authenticate
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code != 200:
        print(f"[FAIL] Authentication")
        return

    token = response.json()["access_token"]
    print(f"[OK] Authenticated\n")

    # Create thread
    response = requests.post(
        f"{BASE_URL}/chat/threads",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Strategic Retrieval Test"}
    )
    thread_id = response.json()["id"]
    print(f"[OK] Created thread: {thread_id}\n")

    # Test 1: Multi-part query that should trigger strategic retrieval
    print("="*80)
    print("TEST: Multi-part incidents database query")
    print("Expected: Multiple query_incidents_database tool calls")
    print("="*80)

    query = """I have two separate questions about the production incidents database:

1. What P1 incidents had resolution times over 100 minutes?
2. Which incidents affected the payment or auth service?

Please answer both questions thoroughly using the incidents database."""

    print(f"\nQuery:\n{query}\n")
    print("-"*80)
    print("Response:\n")

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

    full_response = ""
    tool_calls_detected = 0

    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            data, done = parse_sse_line(line_str)

            if done:
                break

            if data:
                if data.get("type") == "content_delta":
                    delta = data.get("delta", "")
                    print(delta, end='', flush=True)
                    full_response += delta
                elif data.get("type") == "tool_call":
                    tool_calls_detected += 1
                    print(f"\n\n[TOOL CALL #{tool_calls_detected}]", flush=True)

    print("\n")
    print("-"*80)
    print(f"\nResponse length: {len(full_response)} characters")
    print(f"Tool calls detected: {tool_calls_detected}")

    print("\n" + "="*80)
    print(" CHECK LANGSMITH DASHBOARD")
    print("="*80)
    print("\nLook for the trace with the latest timestamp:")
    print("  1. Main trace outputs should show:")
    print("     - tool_calls: Array with details of each call")
    print("     - tool_calls_count: Total number of tool calls")
    print("  2. Child traces for each tool execution:")
    print("     - query_incidents_database calls")
    print("     - Inputs (natural_language_query)")
    print("     - Outputs (sql_query, row_count, sample_results)")
    print("\nThe strategic system prompt should encourage:")
    print("  - Multiple tool calls for multi-part questions")
    print("  - Different queries for different aspects")
    print("  - Comprehensive information gathering")
    print("="*80)


if __name__ == "__main__":
    main()
