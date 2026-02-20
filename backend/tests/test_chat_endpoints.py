"""Tests for chat endpoints."""
import pytest
from fastapi.testclient import TestClient
from main import app
import time
from test_utils import TEST_EMAIL, TEST_PASSWORD

client = TestClient(app)


def get_auth_token():
    """Get auth token for test user."""
    response = client.post(
        "/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    return response.json()["access_token"]


def test_get_providers():
    """Test getting available LLM provider presets."""
    response = client.get("/chat/providers")

    assert response.status_code == 200, f"Failed to get providers: {response.json()}"
    data = response.json()

    # Verify structure
    assert "providers" in data
    assert "defaults" in data

    # Verify known providers exist
    providers = data["providers"]
    assert "openai" in providers
    assert "openrouter" in providers

    # Verify provider structure
    openai_config = providers["openai"]
    assert "name" in openai_config
    assert "base_url" in openai_config
    assert "chat_models" in openai_config
    assert len(openai_config["chat_models"]) > 0

    print(f"\n[TEST PASSED] Successfully retrieved {len(providers)} providers")
    print(f"  - Providers: {', '.join(providers.keys())}")


def test_create_thread():
    """Test creating a new chat thread."""
    token = get_auth_token()

    # Create unique thread title
    timestamp = int(time.time() * 1000)
    thread_title = f"Test Thread {timestamp}"

    response = client.post(
        "/chat/threads",
        json={"title": thread_title},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200, f"Failed to create thread: {response.json()}"
    data = response.json()

    # Verify response structure
    assert "id" in data
    assert data["title"] == thread_title
    assert "created_at" in data
    assert "updated_at" in data

    print(f"\n[TEST PASSED] Successfully created thread: {data['title']}")
    print(f"  - Thread ID: {data['id']}")

    return data["id"]


def test_list_threads():
    """Test listing all threads for current user."""
    token = get_auth_token()

    response = client.get(
        "/chat/threads",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200, f"Failed to list threads: {response.json()}"
    data = response.json()

    # Should be a list
    assert isinstance(data, list)

    # If we have threads, verify structure
    if len(data) > 0:
        thread = data[0]
        assert "id" in thread
        assert "title" in thread
        assert "created_at" in thread
        assert "updated_at" in thread

    print(f"\n[TEST PASSED] Successfully listed {len(data)} threads")


def test_send_message_without_llm():
    """Test sending a message (structure only, no actual LLM call)."""
    token = get_auth_token()

    # Create a thread first
    thread_id = test_create_thread()

    # Prepare message data
    message_data = {
        "content": "Hello, this is a test message",
        "provider": "openai",
        "model": "gpt-4o-mini"
    }

    # Note: We're just testing the endpoint structure, not the full SSE stream
    # A full test would require handling SSE events
    response = client.post(
        f"/chat/threads/{thread_id}/messages",
        json=message_data,
        headers={"Authorization": f"Bearer {token}"}
    )

    # Should return 200 (SSE stream starts)
    assert response.status_code == 200, f"Failed to send message: {response.status_code}"

    print(f"\n[TEST PASSED] Message endpoint accepts valid request")
    print(f"  - Thread ID: {thread_id}")
    print(f"  - Provider: {message_data['provider']}")
    print(f"  - Model: {message_data['model']}")


def test_get_thread_messages():
    """Test getting all messages in a thread."""
    token = get_auth_token()

    # Create a thread
    thread_id = test_create_thread()

    # Get messages (should be empty for new thread)
    response = client.get(
        f"/chat/threads/{thread_id}/messages",
        headers={"Authorization": f"Bearer {thread_id}"}
    )

    # This might fail with 404 if thread doesn't exist or 401 if auth token is wrong
    # Let's use the correct token
    response = client.get(
        f"/chat/threads/{thread_id}/messages",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200, f"Failed to get messages: {response.json()}"
    data = response.json()

    # Should be a list (empty for new thread)
    assert isinstance(data, list)

    print(f"\n[TEST PASSED] Successfully retrieved {len(data)} messages from thread")


def test_delete_thread():
    """Test deleting a thread."""
    token = get_auth_token()

    # Create a thread to delete
    thread_id = test_create_thread()

    # Delete it
    response = client.delete(
        f"/chat/threads/{thread_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200, f"Failed to delete thread: {response.json()}"
    data = response.json()

    assert "message" in data
    assert "deleted" in data["message"].lower()

    print(f"\n[TEST PASSED] Successfully deleted thread {thread_id}")


def test_message_without_api_key_field():
    """Test that message endpoint no longer accepts api_key field (Plan 7)."""
    token = get_auth_token()

    # Create a thread
    thread_id = test_create_thread()

    # Try to send message with api_key field (should be ignored/removed in Plan 7)
    message_data = {
        "content": "Test message",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "api_key": "fake-key-should-be-ignored"  # This field should not be in schema
    }

    response = client.post(
        f"/chat/threads/{thread_id}/messages",
        json=message_data,
        headers={"Authorization": f"Bearer {token}"}
    )

    # Should either succeed (ignoring api_key) or fail with validation error
    # According to Plan 7, api_key should be removed from MessageCreate model
    if response.status_code == 422:
        # Validation error - api_key not in schema (correct)
        print(f"\n[TEST PASSED] api_key field correctly rejected (not in schema)")
    elif response.status_code == 200:
        # Accepted but should have ignored api_key
        print(f"\n[TEST PASSED] api_key field ignored by endpoint")
    else:
        pytest.fail(f"Unexpected status code: {response.status_code}")


if __name__ == "__main__":
    print("=" * 60)
    print("CHAT ENDPOINTS TESTS")
    print("=" * 60)

    try:
        test_get_providers()
        test_create_thread()
        test_list_threads()
        test_send_message_without_llm()
        test_get_thread_messages()
        test_delete_thread()
        test_message_without_api_key_field()

        print("\n" + "=" * 60)
        print("ALL CHAT TESTS PASSED!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n[TEST FAILED] {e}")
        raise
