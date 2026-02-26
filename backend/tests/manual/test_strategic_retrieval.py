"""
MANUAL TEST - Requires a live server.
  Run: cd backend && uvicorn main:app --reload
  Then: python tests/manual/test_strategic_retrieval.py

Test strategic retrieval with multiple tool calls.

This test demonstrates the enhanced system prompt that encourages
the LLM to generate a retrieval strategy and make multiple tool calls.
"""
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Get test credentials from environment
TEST_EMAIL = os.getenv("TEST_EMAIL")
TEST_PASSWORD = os.getenv("TEST_PASSWORD")

BASE_URL = "http://localhost:8000"


def get_auth_token():
    """Authenticate and get access token."""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code != 200:
        print(f"[FAIL] Authentication failed: {response.json()}")
        return None
    print(f"[OK] Authenticated as {TEST_EMAIL}")
    return response.json()["access_token"]


def create_thread(token):
    """Create a new chat thread."""
    response = requests.post(
        f"{BASE_URL}/chat/threads",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Strategic Retrieval Test"}
    )
    if response.status_code not in [200, 201]:
        print(f"[FAIL] Thread creation failed: {response.json()}")
        return None

    thread_id = response.json()["id"]
    print(f"[OK] Created thread: {thread_id}")
    return thread_id


def run_strategic_retrieval(token, thread_id):
    """Test strategic retrieval with a complex query."""

    # Test Query 1: Should trigger multiple retrieve_documents calls
    # (different aspects: main themes, technical details, conclusions)
    print("\n" + "="*80)
    print("TEST 1: Complex document query (should trigger multiple retrieval calls)")
    print("="*80)

    query1 = """Search through my uploaded documents and tell me:
    1. What are the main themes and topics?
    2. What technical specifications or important details are mentioned?
    3. What conclusions or recommendations are provided?

    Use multiple search queries to find this information across different parts of the documents."""

    response = requests.post(
        f"{BASE_URL}/chat/threads/{thread_id}/messages",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "content": query1,
            "provider": "openai",
            "model": "gpt-4o-mini"
        },
        stream=True
    )

    if response.status_code != 200:
        print(f"[FAIL] Chat request failed: {response.text}")
        return

    print("\n Response:")
    full_response = ""
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = line[6:]  # Remove 'data: ' prefix
                if data.strip() == '[DONE]':
                    break
                try:
                    chunk = json.loads(data)
                    # Handle content_delta type (streaming chunks)
                    if chunk.get('type') == 'content_delta' and 'delta' in chunk:
                        print(chunk['delta'], end='', flush=True)
                        full_response += chunk['delta']
                    # Handle legacy format with 'content' key (if any)
                    elif 'content' in chunk:
                        print(chunk['content'], end='', flush=True)
                        full_response += chunk['content']
                    if 'sources' in chunk and chunk['sources']:
                        print(f"\n\n Sources: {len(chunk['sources'])} chunks retrieved")
                except json.JSONDecodeError:
                    pass

    print("\n\n" + "="*80)
    print("[OK] Test 1 completed")
    print("="*80)

    # Test Query 2: Should trigger retrieve_documents + web_search
    print("\n" + "="*80)
    print("TEST 2: Hybrid query (documents + current info)")
    print("="*80)

    query2 = """Based on the documents, what are the key concepts?
    Also, what are the current industry trends related to these concepts?
    (Use both documents and web search to provide a complete answer)"""

    response = requests.post(
        f"{BASE_URL}/chat/threads/{thread_id}/messages",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "content": query2,
            "provider": "openai",
            "model": "gpt-4o-mini"
        },
        stream=True
    )

    if response.status_code != 200:
        print(f"[FAIL] Chat request failed: {response.text}")
        return

    print("\n Response:")
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = line[6:]
                if data.strip() == '[DONE]':
                    break
                try:
                    chunk = json.loads(data)
                    if chunk.get('type') == 'content_delta' and 'delta' in chunk:
                        print(chunk['delta'], end='', flush=True)
                    elif 'content' in chunk:
                        print(chunk['content'], end='', flush=True)
                except json.JSONDecodeError:
                    pass

    print("\n\n" + "="*80)
    print("[OK] Test 2 completed")
    print("="*80)

    # Test Query 3: Should trigger query_deployments_database
    print("\n" + "="*80)
    print("TEST 3: Incidents database query")
    print("="*80)

    query3 = """What P1 incidents are in the database?
    Also show me incidents that affected the payment or auth service."""

    response = requests.post(
        f"{BASE_URL}/chat/threads/{thread_id}/messages",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "content": query3,
            "provider": "openai",
            "model": "gpt-4o-mini"
        },
        stream=True
    )

    if response.status_code != 200:
        print(f"[FAIL] Chat request failed: {response.text}")
        return

    print("\n Response:")
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = line[6:]
                if data.strip() == '[DONE]':
                    break
                try:
                    chunk = json.loads(data)
                    if chunk.get('type') == 'content_delta' and 'delta' in chunk:
                        print(chunk['delta'], end='', flush=True)
                    elif 'content' in chunk:
                        print(chunk['content'], end='', flush=True)
                except json.JSONDecodeError:
                    pass

    print("\n\n" + "="*80)
    print("[OK] Test 3 completed")
    print("="*80)


def main():
    """Run strategic retrieval tests."""
    print("\n" + "="*80)
    print(" STRATEGIC RETRIEVAL TEST - MANUAL VALIDATION REQUIRED")
    print("="*80)
    print("\n[IMPORTANT] This test requires:")
    print("  1. Documents already uploaded to the test account")
    print("  2. Manual validation via LangSmith dashboard")
    print("  3. LangSmith tracing enabled (LANGCHAIN_TRACING_V2=true)")
    print("\n[NOTE] This test demonstrates agentic behavior but does NOT")
    print("       automatically verify results. YOU must inspect LangSmith")
    print("       traces to validate strategic tool calling patterns.")
    print("="*80)

    if not TEST_EMAIL or not TEST_PASSWORD:
        print("\n[FAIL] TEST_EMAIL and TEST_PASSWORD must be set in .env file")
        return

    # Authenticate
    token = get_auth_token()
    if not token:
        return

    # Create thread
    thread_id = create_thread(token)
    if not thread_id:
        return

    # Run tests
    run_strategic_retrieval(token, thread_id)

    print("\n" + "="*80)
    print(" CHECK LANGSMITH DASHBOARD")
    print("="*80)
    print("Go to LangSmith to see:")
    print("  • How many tool calls were made")
    print("  • What inputs/outputs each tool received")
    print("  • The strategic retrieval pattern used")
    print("="*80)


if __name__ == "__main__":
    main()
