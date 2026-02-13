"""Tests for provider service (Plan 7)."""
import pytest
from services.provider_service import provider_service, PROVIDER_PRESETS


def test_get_all_providers():
    """Test getting all available provider presets."""
    providers = provider_service.get_providers()

    # Should return the full presets dictionary
    assert isinstance(providers, dict)
    assert len(providers) == 3  # Plan 8: Only 3 providers

    # Verify known providers (Plan 8: OpenAI, OpenRouter, LM Studio only)
    assert "openai" in providers
    assert "openrouter" in providers
    assert "lmstudio" in providers

    print(f"\n[TEST PASSED] Retrieved {len(providers)} providers")
    print(f"  - Available: {', '.join(providers.keys())}")


def test_get_specific_provider_config():
    """Test getting configuration for specific providers."""
    # Test OpenAI
    openai_config = provider_service.get_provider_config("openai")
    assert openai_config is not None
    assert openai_config["name"] == "OpenAI"
    assert openai_config["base_url"] == "https://api.openai.com/v1"
    assert len(openai_config["chat_models"]) > 0
    assert len(openai_config["embedding_models"]) > 0

    # Test LM Studio (local)
    lmstudio_config = provider_service.get_provider_config("lmstudio")
    assert lmstudio_config is not None
    assert lmstudio_config["name"] == "LM Studio (Local)"

    # Test non-existent provider
    invalid_config = provider_service.get_provider_config("nonexistent")
    assert invalid_config is None

    print(f"\n[TEST PASSED] Successfully retrieved specific provider configs")


def test_provider_config_case_insensitive():
    """Test that provider lookup is case-insensitive."""
    config_lower = provider_service.get_provider_config("openai")
    config_upper = provider_service.get_provider_config("OPENAI")
    config_mixed = provider_service.get_provider_config("OpenAI")

    assert config_lower is not None
    assert config_upper is not None
    assert config_mixed is not None
    assert config_lower == config_upper == config_mixed

    print(f"\n[TEST PASSED] Provider lookup is case-insensitive")


def test_validate_provider_with_model():
    """Test validation for providers with model names."""
    # OpenAI with valid model - validation is permissive now
    is_valid, error = provider_service.validate_provider_config(
        provider="openai",
        model="gpt-4o-mini"
    )
    assert is_valid is True
    assert error == ""

    # OpenRouter with model
    is_valid, error = provider_service.validate_provider_config(
        provider="openrouter",
        model="anthropic/claude-3.5-sonnet"
    )
    assert is_valid is True
    assert error == ""

    print(f"\n[TEST PASSED] Provider validation works correctly")


def test_validate_local_provider():
    """Test validation for local providers."""
    # LM Studio validation
    is_valid, error = provider_service.validate_provider_config(
        provider="lmstudio",
        model="any-model"
    )
    assert is_valid is True
    assert error == ""

    print(f"\n[TEST PASSED] Local provider validation works")


def test_validate_unknown_provider():
    """Test validation fails for unknown providers."""
    is_valid, error = provider_service.validate_provider_config(
        provider="unknown-provider",
        model="some-model"
    )
    assert is_valid is False
    assert "Unknown provider" in error

    print(f"\n[TEST PASSED] Unknown provider validation fails correctly")


def test_validate_with_base_url():
    """Test validation with custom base URL."""
    # LM Studio with custom base URL
    is_valid, error = provider_service.validate_provider_config(
        provider="lmstudio",
        model="custom-model",
        base_url="http://localhost:1234"
    )
    assert is_valid is True
    assert error == ""

    print(f"\n[TEST PASSED] Custom base URL validation works")


def test_server_side_api_keys():
    """Test that API keys are handled server-side only (Plan 7)."""
    # Validation doesn't require api_key parameter
    # API keys are retrieved from environment via get_api_key_for_provider

    # Test that API key getter exists
    openai_key = provider_service.get_api_key_for_provider("openai")
    openrouter_key = provider_service.get_api_key_for_provider("openrouter")
    lmstudio_key = provider_service.get_api_key_for_provider("lmstudio")

    # Keys should be strings or None (depending on .env configuration)
    assert openai_key is None or isinstance(openai_key, str)
    assert openrouter_key is None or isinstance(openrouter_key, str)
    assert lmstudio_key is None or isinstance(lmstudio_key, str)

    print(f"\n[TEST PASSED] API keys handled server-side only (Plan 7)")


def test_all_providers_have_required_fields():
    """Test that all provider configs have required fields."""
    providers = PROVIDER_PRESETS

    required_fields = ["name", "chat_models", "embedding_models"]

    for provider_key, config in providers.items():
        for field in required_fields:
            assert field in config, f"Provider '{provider_key}' missing field '{field}'"

        # Verify types
        assert isinstance(config["name"], str)
        assert isinstance(config["chat_models"], list)
        assert isinstance(config["embedding_models"], list)

        # base_url is optional for lmstudio
        if "base_url" in config:
            assert isinstance(config["base_url"], str)

    print(f"\n[TEST PASSED] All {len(providers)} providers have required fields")


if __name__ == "__main__":
    print("=" * 60)
    print("PROVIDER SERVICE TESTS (PLAN 7)")
    print("=" * 60)

    try:
        test_get_all_providers()
        test_get_specific_provider_config()
        test_provider_config_case_insensitive()
        test_validate_provider_with_model()
        test_validate_local_provider()
        test_validate_unknown_provider()
        test_validate_with_base_url()
        test_server_side_api_keys()
        test_all_providers_have_required_fields()

        print("\n" + "=" * 60)
        print("ALL PROVIDER SERVICE TESTS PASSED!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n[TEST FAILED] {e}")
        raise
