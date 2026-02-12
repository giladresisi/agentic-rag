"""Tests for provider service (Plan 7)."""
import pytest
from services.provider_service import provider_service, PROVIDER_PRESETS


def test_get_all_providers():
    """Test getting all available provider presets."""
    providers = provider_service.get_providers()

    # Should return the full presets dictionary
    assert isinstance(providers, dict)
    assert len(providers) > 0

    # Verify known providers
    assert "openai" in providers
    assert "ollama" in providers
    assert "openrouter" in providers
    assert "lmstudio" in providers
    assert "custom" in providers

    print(f"\n[TEST PASSED] Retrieved {len(providers)} providers")
    print(f"  - Available: {', '.join(providers.keys())}")


def test_get_specific_provider_config():
    """Test getting configuration for specific providers."""
    # Test OpenAI
    openai_config = provider_service.get_provider_config("openai")
    assert openai_config is not None
    assert openai_config["name"] == "OpenAI"
    assert openai_config["base_url"] == "https://api.openai.com/v1"
    assert openai_config["requires_api_key"] is True
    assert len(openai_config["models"]) > 0

    # Test Ollama (local, no API key)
    ollama_config = provider_service.get_provider_config("ollama")
    assert ollama_config is not None
    assert ollama_config["name"] == "Ollama (Local)"
    assert ollama_config["requires_api_key"] is False

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


def test_validate_provider_with_api_key_required():
    """Test validation for providers that require API keys."""
    # OpenAI requires API key - should pass if default key available
    is_valid, error = provider_service.validate_provider_config(
        provider="openai",
        model="gpt-4o-mini",
        has_default_api_key=True
    )
    assert is_valid is True
    assert error == ""

    # OpenAI requires API key - should fail if no default key
    is_valid, error = provider_service.validate_provider_config(
        provider="openai",
        model="gpt-4o-mini",
        has_default_api_key=False
    )
    assert is_valid is False
    assert "requires an API key" in error

    print(f"\n[TEST PASSED] API key requirement validation works correctly")


def test_validate_provider_without_api_key():
    """Test validation for providers that don't require API keys (local)."""
    # Ollama doesn't require API key
    is_valid, error = provider_service.validate_provider_config(
        provider="ollama",
        model="llama3.2",
        has_default_api_key=False
    )
    assert is_valid is True
    assert error == ""

    # LM Studio doesn't require API key
    is_valid, error = provider_service.validate_provider_config(
        provider="lmstudio",
        model="any-model",
        has_default_api_key=False
    )
    assert is_valid is True
    assert error == ""

    print(f"\n[TEST PASSED] Local providers work without API key")


def test_validate_unknown_provider():
    """Test validation fails for unknown providers."""
    is_valid, error = provider_service.validate_provider_config(
        provider="unknown-provider",
        model="some-model",
        has_default_api_key=True
    )
    assert is_valid is False
    assert "Unknown provider" in error

    print(f"\n[TEST PASSED] Unknown provider validation fails correctly")


def test_validate_custom_provider():
    """Test validation for custom provider."""
    # Custom provider requires API key by default
    is_valid, error = provider_service.validate_provider_config(
        provider="custom",
        model="custom-model",
        base_url="https://custom.api.com/v1",
        has_default_api_key=True
    )
    assert is_valid is True
    assert error == ""

    # Custom provider without API key should fail
    is_valid, error = provider_service.validate_provider_config(
        provider="custom",
        model="custom-model",
        has_default_api_key=False
    )
    assert is_valid is False

    print(f"\n[TEST PASSED] Custom provider validation works")


def test_api_key_removed_from_validation():
    """Test that api_key parameter is removed from validation (Plan 7)."""
    # According to Plan 7, api_key parameter should be removed
    # The function should only check has_default_api_key

    # This should work - using server's default key
    is_valid, error = provider_service.validate_provider_config(
        provider="openai",
        model="gpt-4o-mini",
        has_default_api_key=True
    )
    assert is_valid is True

    print(f"\n[TEST PASSED] Validation uses server-side API key only (Plan 7)")


def test_all_providers_have_required_fields():
    """Test that all provider configs have required fields."""
    providers = PROVIDER_PRESETS

    required_fields = ["name", "base_url", "requires_api_key", "models"]

    for provider_key, config in providers.items():
        for field in required_fields:
            assert field in config, f"Provider '{provider_key}' missing field '{field}'"

        # Verify types
        assert isinstance(config["name"], str)
        assert isinstance(config["base_url"], str)
        assert isinstance(config["requires_api_key"], bool)
        assert isinstance(config["models"], list)

    print(f"\n[TEST PASSED] All {len(providers)} providers have required fields")


if __name__ == "__main__":
    print("=" * 60)
    print("PROVIDER SERVICE TESTS (PLAN 7)")
    print("=" * 60)

    try:
        test_get_all_providers()
        test_get_specific_provider_config()
        test_provider_config_case_insensitive()
        test_validate_provider_with_api_key_required()
        test_validate_provider_without_api_key()
        test_validate_unknown_provider()
        test_validate_custom_provider()
        test_api_key_removed_from_validation()
        test_all_providers_have_required_fields()

        print("\n" + "=" * 60)
        print("ALL PROVIDER SERVICE TESTS PASSED!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n[TEST FAILED] {e}")
        raise
