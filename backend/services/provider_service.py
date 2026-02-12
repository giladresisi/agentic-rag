"""Provider presets for different LLM providers."""

from typing import Dict, List, Any

# Provider presets with base URLs and available models
PROVIDER_PRESETS: Dict[str, Any] = {
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "requires_api_key": True,
        "models": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ]
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "requires_api_key": True,
        "models": [
            "anthropic/claude-3.5-sonnet",
            "anthropic/claude-3-opus",
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "meta-llama/llama-3.1-405b-instruct",
            "google/gemini-pro-1.5",
        ]
    },
    "ollama": {
        "name": "Ollama (Local)",
        "base_url": "http://localhost:11434/v1",
        "requires_api_key": False,
        "models": [
            "llama3.2",
            "llama3.1",
            "mistral",
            "mixtral",
            "qwen2.5",
        ]
    },
    "lmstudio": {
        "name": "LM Studio (Local)",
        "base_url": "http://localhost:1234/v1",
        "requires_api_key": False,
        "models": []  # LM Studio models depend on what user has loaded
    },
    "custom": {
        "name": "Custom",
        "base_url": "",
        "requires_api_key": True,
        "models": []  # User provides their own model name
    }
}


class ProviderService:
    """Service for managing LLM provider configurations."""

    @staticmethod
    def get_providers() -> Dict[str, Any]:
        """Get all available provider presets.

        Returns:
            Dictionary of provider configurations
        """
        return PROVIDER_PRESETS

    @staticmethod
    def get_provider_config(provider: str) -> Dict[str, Any] | None:
        """Get configuration for a specific provider.

        Args:
            provider: Provider identifier (e.g., 'openai', 'ollama')

        Returns:
            Provider configuration or None if not found
        """
        return PROVIDER_PRESETS.get(provider.lower())

    @staticmethod
    def validate_provider_config(
        provider: str,
        model: str,
        base_url: str | None = None,
        has_default_api_key: bool = True
    ) -> tuple[bool, str]:
        """Validate provider configuration.

        Args:
            provider: Provider identifier
            model: Model name
            base_url: Optional custom base URL
            has_default_api_key: Whether a default API key is available

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Get provider config
        config = PROVIDER_PRESETS.get(provider.lower())
        if not config:
            return False, f"Unknown provider: {provider}"

        # Validate API key requirement
        # Only fail if provider requires API key AND no default available
        if config["requires_api_key"] and not has_default_api_key:
            return False, f"Provider '{provider}' requires an API key (must be configured on server)"

        # Model validation is now permissive - allow any model name
        # Providers will return their own errors if model is invalid

        return True, ""


provider_service = ProviderService()
