"""Tests for auth endpoints."""
import pytest
from fastapi.testclient import TestClient
from main import app
from test_utils import TEST_EMAIL, TEST_PASSWORD

client = TestClient(app)


def test_login_success():
    """Test successful login with existing user."""
    response = client.post(
        "/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )

    assert response.status_code == 200, f"Login failed: {response.json()}"
    data = response.json()

    # Verify response structure
    assert "access_token" in data
    assert "user" in data

    # Verify user data
    user = data["user"]
    assert "id" in user
    assert user["email"] == TEST_EMAIL

    print(f"\n[TEST PASSED] Successfully logged in as {TEST_EMAIL}")
    print(f"  - User ID: {user['id']}")


def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    response = client.post(
        "/auth/login",
        json={"email": TEST_EMAIL, "password": "wrong-password"}
    )

    # Should return 401 Unauthorized
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    print(f"\n[TEST PASSED] Invalid credentials correctly rejected")


def test_login_missing_fields():
    """Test login with missing required fields."""
    # Missing password
    response = client.post(
        "/auth/login",
        json={"email": TEST_EMAIL}
    )
    assert response.status_code == 422, "Should fail validation with missing password"

    # Missing email
    response = client.post(
        "/auth/login",
        json={"password": TEST_PASSWORD}
    )
    assert response.status_code == 422, "Should fail validation with missing email"

    print(f"\n[TEST PASSED] Missing fields correctly rejected")


def test_get_current_user():
    """Test getting current user with valid token."""
    # First login to get token
    login_response = client.post(
        "/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Get current user
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200, f"Failed to get current user: {response.json()}"
    data = response.json()

    # Verify user data
    assert "id" in data
    assert "email" in data
    assert data["email"] == TEST_EMAIL

    print(f"\n[TEST PASSED] Successfully retrieved current user")
    print(f"  - Email: {data['email']}")


def test_get_current_user_no_token():
    """Test getting current user without auth token."""
    response = client.get("/auth/me")

    # Should return 401 Unauthorized
    assert response.status_code == 401 or response.status_code == 403

    print(f"\n[TEST PASSED] Request without token correctly rejected")


def test_get_current_user_invalid_token():
    """Test getting current user with invalid token."""
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token-12345"}
    )

    # Should return 401 Unauthorized
    assert response.status_code == 401 or response.status_code == 403

    print(f"\n[TEST PASSED] Invalid token correctly rejected")


def test_logout():
    """Test logout endpoint."""
    # First login
    login_response = client.post(
        "/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Logout
    response = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200, f"Logout failed: {response.json()}"
    data = response.json()

    assert "message" in data

    print(f"\n[TEST PASSED] Successfully logged out")


def test_protected_endpoint_requires_auth():
    """Test that protected endpoints require authentication."""
    # Try to access protected endpoint without token
    response = client.get("/chat/threads")

    # Should return 401 or 403
    assert response.status_code in [401, 403], \
        f"Protected endpoint should require auth, got {response.status_code}"

    print(f"\n[TEST PASSED] Protected endpoints require authentication")


def test_token_format():
    """Test that token follows expected format."""
    response = client.post(
        "/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200

    data = response.json()
    token = data["access_token"]

    # JWT tokens have 3 parts separated by dots
    parts = token.split('.')
    assert len(parts) == 3, "JWT should have 3 parts (header.payload.signature)"

    # Each part should be base64-encoded (non-empty)
    for part in parts:
        assert len(part) > 0, "JWT parts should not be empty"

    print(f"\n[TEST PASSED] Token follows JWT format")


if __name__ == "__main__":
    print("=" * 60)
    print("AUTH ENDPOINTS TESTS")
    print("=" * 60)

    try:
        test_login_success()
        test_login_invalid_credentials()
        test_login_missing_fields()
        test_get_current_user()
        test_get_current_user_no_token()
        test_get_current_user_invalid_token()
        test_logout()
        test_protected_endpoint_requires_auth()
        test_token_format()

        print("\n" + "=" * 60)
        print("ALL AUTH TESTS PASSED!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n[TEST FAILED] {e}")
        raise
