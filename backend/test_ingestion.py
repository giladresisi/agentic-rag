"""Tests for ingestion endpoints."""
import pytest
from fastapi.testclient import TestClient
from main import app
from io import BytesIO
import os
import time

# Test credentials
TEST_EMAIL = "test@..."
TEST_PASSWORD = "***"

client = TestClient(app)


def get_auth_token():
    """Get auth token for test user."""
    response = client.post(
        "/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    return response.json()["access_token"]


def test_upload_markdown_file():
    """Test uploading a valid markdown file."""
    # Get auth token
    token = get_auth_token()

    # Create a test markdown file with unique name
    timestamp = int(time.time() * 1000)
    filename = f"test_document_{timestamp}.md"

    md_content = b"""# Test Document

This is a test markdown file for ingestion testing.

## Section 1
Some content here.

## Section 2
More content here.
"""

    # Create file-like object
    files = {
        "file": (filename, BytesIO(md_content), "text/markdown")
    }

    # Upload the file
    response = client.post(
        "/ingestion/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"}
    )

    # Verify response
    assert response.status_code == 200, f"Upload failed: {response.json()}"
    data = response.json()

    # Verify response data
    assert data["filename"] == filename
    assert data["status"] == "processing"
    assert data["file_size_bytes"] == len(md_content)
    assert "id" in data
    assert "created_at" in data

    print(f"\n[TEST PASSED] Successfully uploaded markdown file: {data['filename']}")
    print(f"  - Document ID: {data['id']}")
    print(f"  - File size: {data['file_size_bytes']} bytes")
    print(f"  - Status: {data['status']}")

    return data["id"]


def test_upload_unsupported_file_type():
    """Test uploading an unsupported file type (PNG)."""
    token = get_auth_token()

    # Create a fake PNG file
    png_content = b"fake png content"
    files = {
        "file": ("screenshot.png", BytesIO(png_content), "image/png")
    }

    # Attempt upload
    response = client.post(
        "/ingestion/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"}
    )

    # Verify rejection
    assert response.status_code == 400, "Expected 400 for unsupported file type"
    error = response.json()

    # Verify error message includes filename and extension
    assert "screenshot.png" in error["detail"]
    assert ".png" in error["detail"]
    assert "Unsupported file type" in error["detail"]

    print(f"\n[TEST PASSED] Correctly rejected PNG file")
    print(f"  - Error message: {error['detail']}")


def test_upload_oversized_file():
    """Test uploading a file that exceeds size limit."""
    token = get_auth_token()

    # Create a file larger than 10MB
    large_content = b"x" * (11 * 1024 * 1024)  # 11MB
    files = {
        "file": ("large_file.md", BytesIO(large_content), "text/markdown")
    }

    # Attempt upload
    response = client.post(
        "/ingestion/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"}
    )

    # Verify rejection
    assert response.status_code == 400, "Expected 400 for oversized file"
    error = response.json()

    # Verify error message includes filename and size
    assert "large_file.md" in error["detail"]
    assert "too large" in error["detail"]
    assert "11.0MB" in error["detail"]

    print(f"\n[TEST PASSED] Correctly rejected oversized file")
    print(f"  - Error message: {error['detail']}")


if __name__ == "__main__":
    print("=" * 60)
    print("INGESTION UPLOAD TESTS")
    print("=" * 60)

    try:
        # Run tests
        test_upload_markdown_file()
        test_upload_unsupported_file_type()
        test_upload_oversized_file()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n[TEST FAILED] {e}")
        raise
