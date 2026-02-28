"""Tests for /health/warmup endpoint."""
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_warmup_endpoint_returns_correct_structure(client):
    """GET /health/warmup returns {ready: bool, error: str|null}."""
    response = client.get("/health/warmup")
    assert response.status_code == 200
    data = response.json()
    assert "ready" in data
    assert isinstance(data["ready"], bool)
    assert "error" in data
    assert data["error"] is None or isinstance(data["error"], str)


def test_warmup_endpoint_no_auth_required(client):
    """Warmup status is public — no Authorization header needed."""
    response = client.get("/health/warmup")
    assert response.status_code == 200


def test_warmup_error_path_unblocks_upload():
    """When warmup fails, ready is set to True and error is captured (upload UI unblocks)."""
    import main
    from unittest.mock import patch
    original = dict(main._warmup_state)
    main._warmup_state.update({"ready": False, "error": None})
    try:
        with patch("services.embedding_service.warmup_converter", side_effect=Exception("model load failed")):
            main._background_warmup()
        assert main._warmup_state["ready"] is True
        assert main._warmup_state["error"] is not None
        assert "model load failed" in main._warmup_state["error"]
    finally:
        main._warmup_state.update(original)
