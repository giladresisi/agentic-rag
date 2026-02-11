"""
Comprehensive tests for OpenAI Responses API integration.
Tests streaming, message saving, and vector store integration.
"""
import asyncio
import httpx
from services.supabase_service import get_supabase
from services.openai_service import openai_service

# Test credentials
TEST_EMAIL = "test@test.com"
TEST_PASSWORD = "123456"
API_BASE_URL = "http://localhost:8000"


def get_auth_token():
    """Get authentication token for test user."""
    supabase = get_supabase()
    response = supabase.auth.sign_in_with_password({
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    return response.session.access_token, response.user.id


async def test_openai_service_direct():
    """Test 1: OpenAI service streaming directly."""
    print("\n=== TEST 1: OpenAI Service Direct ===")

    try:
        conversation_history = [
            {"role": "user", "content": "Say 'Hello World' and nothing else."}
        ]

        print("Streaming response from OpenAI...")
        full_response = ""
        chunk_count = 0

        async for delta in openai_service.stream_response(conversation_history):
            full_response += delta
            chunk_count += 1
            print(f"  Chunk {chunk_count}: {repr(delta)}")

        print(f"\nFull response: {full_response}")
        print(f"Total chunks: {chunk_count}")

        if full_response.strip():
            print("[OK] TEST 1 PASSED: OpenAI service streaming works")
            return True
        else:
            print("[FAIL] TEST 1 FAILED: Empty response from OpenAI")
            return False

    except Exception as e:
        print(f"[FAIL] TEST 1 FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_send_message_api():
    """Test 2: Full message sending via API endpoint."""
    print("\n=== TEST 2: Send Message API Endpoint ===")

    try:
        token, user_id = get_auth_token()
        print(f"Authenticated as user: {user_id}")

        supabase = get_supabase()

        # Create a new thread via API (to avoid RLS issues)
        async with httpx.AsyncClient(timeout=30.0) as client:
            create_thread_resp = await client.post(
                f"{API_BASE_URL}/chat/threads",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json={"title": "Test Thread"}
            )

            if create_thread_resp.status_code != 200:
                print(f"[FAIL] TEST 2 FAILED: Failed to create thread - {create_thread_resp.status_code}")
                return False

            thread_data = create_thread_resp.json()
            thread_id = thread_data["id"]
            print(f"Created test thread: {thread_id}")

        # Count messages before
        messages_before = supabase.table("messages")\
            .select("*", count="exact")\
            .eq("thread_id", thread_id)\
            .execute()
        count_before = messages_before.count
        print(f"Messages before: {count_before}")

        # Send message via API
        print("\nSending message via API...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{API_BASE_URL}/chat/threads/{thread_id}/messages"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            data = {"content": "Reply with exactly: 'Test successful'"}

            # Stream the response
            chunks_received = []
            full_response = ""

            async with client.stream("POST", url, headers=headers, json=data) as response:
                if response.status_code != 200:
                    print(f"[FAIL] TEST 2 FAILED: API returned {response.status_code}")
                    print(f"Response: {await response.aread()}")
                    return False

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_content = line[6:]  # Remove "data: " prefix
                        if data_content == "[DONE]":
                            print("  Received [DONE]")
                            break

                        try:
                            import json
                            event_data = json.loads(data_content)
                            if event_data.get("type") == "content_delta":
                                delta = event_data.get("delta", "")
                                full_response += delta
                                chunks_received.append(delta)
                                print(f"  Chunk {len(chunks_received)}: {repr(delta)}")
                        except json.JSONDecodeError:
                            continue

        print(f"\nFull streamed response: {full_response}")
        print(f"Total chunks received: {len(chunks_received)}")

        # Wait a moment for DB writes
        await asyncio.sleep(1)

        # Count messages after
        messages_after = supabase.table("messages")\
            .select("*", count="exact")\
            .eq("thread_id", thread_id)\
            .execute()
        count_after = messages_after.count
        print(f"\nMessages after: {count_after}")

        # Should have 2 new messages (user + assistant)
        expected_count = count_before + 2
        if count_after == expected_count:
            print(f"[OK] TEST 2 PASSED: {count_after - count_before} messages saved")
            return True
        else:
            print(f"[FAIL] TEST 2 FAILED: Expected {expected_count} messages, got {count_after}")
            return False

    except Exception as e:
        print(f"[FAIL] TEST 2 FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_vector_store_config():
    """Test 3: Vector store configuration."""
    print("\n=== TEST 3: Vector Store Configuration ===")

    try:
        from config import settings

        if settings.OPENAI_VECTOR_STORE_ID:
            print(f"Vector store ID configured: {settings.OPENAI_VECTOR_STORE_ID[:20]}...")
            print("[OK] TEST 3 PASSED: Vector store is configured")
            return True
        else:
            print("[WARN] TEST 3 WARNING: Vector store not configured (optional)")
            print("  Set OPENAI_VECTOR_STORE_ID in .env to enable RAG")
            return True

    except Exception as e:
        print(f"[FAIL] TEST 3 FAILED: {type(e).__name__}: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("OPENAI RESPONSES API TEST SUITE")
    print("=" * 60)

    results = []

    # Test 1: Direct OpenAI service
    results.append(await test_openai_service_direct())

    # Test 2: Full API endpoint
    results.append(await test_send_message_api())

    # Test 3: Vector store config
    results.append(await test_vector_store_config())

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n[OK] ALL TESTS PASSED")
        return 0
    else:
        print(f"\n[FAIL] {total - passed} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
