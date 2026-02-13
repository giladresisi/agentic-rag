"""Provider presets for different LLM providers."""

from openai import AsyncOpenAI
from typing import Dict, List, Any, AsyncGenerator, Optional
from config import settings
from urllib.parse import urlparse
import ipaddress

# Provider presets with base URLs, chat models, and embedding models
PROVIDER_PRESETS: Dict[str, Any] = {
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "chat_models": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ],
        "embedding_models": [
            {"name": "text-embedding-3-small", "dimensions": 1536},
            {"name": "text-embedding-3-large", "dimensions": 3072},
            {"name": "text-embedding-ada-002", "dimensions": 1536},
        ]
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "chat_models": [
            "anthropic/claude-3.5-sonnet",
            "anthropic/claude-3-opus",
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "meta-llama/llama-3.1-405b-instruct",
            "google/gemini-pro-1.5",
        ],
        "embedding_models": []
    },
    "lmstudio": {
        "name": "LM Studio (Local)",
        "chat_models": [],
        "embedding_models": []
    },
}


class ProviderService:
    """Service for managing LLM provider configurations."""

    @staticmethod
    def _validate_base_url(url: str, provider: str) -> tuple[bool, str]:
        """Validate base URL to prevent SSRF attacks.

        Args:
            url: The base URL to validate
            provider: Provider identifier (lmstudio allows localhost)

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            parsed = urlparse(url)

            # Require valid scheme
            if parsed.scheme not in ['http', 'https']:
                return False, "URL must use http or https scheme"

            # LM Studio is allowed to use localhost
            if provider.lower() == "lmstudio":
                # Allow localhost/127.0.0.1 for local LM Studio
                if parsed.hostname in ['localhost', '127.0.0.1', '::1']:
                    return True, ""

            # For non-LM Studio providers, enforce HTTPS and block private IPs
            if parsed.scheme != 'https':
                return False, "External providers must use HTTPS"

            # Block private IP ranges and localhost
            if parsed.hostname:
                try:
                    ip = ipaddress.ip_address(parsed.hostname)
                    if ip.is_private or ip.is_loopback or ip.is_link_local:
                        return False, "Private IP addresses are not allowed"
                except ValueError:
                    # Not an IP address, it's a hostname - allowed
                    pass

                # Block localhost hostnames
                if parsed.hostname.lower() in ['localhost', '127.0.0.1', '::1']:
                    return False, "Localhost is not allowed for external providers"

            return True, ""

        except Exception as e:
            return False, f"Invalid URL format: {str(e)}"

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
            provider: Provider identifier (e.g., 'openai', 'openrouter', 'lmstudio')

        Returns:
            Provider configuration or None if not found
        """
        return PROVIDER_PRESETS.get(provider.lower())

    @staticmethod
    def _get_api_key_for_provider(provider: str) -> str | None:
        """Get the API key for a specific provider.

        Args:
            provider: Provider identifier

        Returns:
            API key string or None if not configured
        """
        provider = provider.lower()
        if provider == "openai":
            return settings.OPENAI_API_KEY
        elif provider == "openrouter":
            return settings.OPENROUTER_API_KEY
        elif provider == "lmstudio":
            return settings.LM_STUDIO_API_KEY
        return None

    @staticmethod
    def get_api_key_for_provider(provider: str) -> str | None:
        """Public accessor for provider API key.

        Args:
            provider: Provider identifier

        Returns:
            API key string or None if not configured
        """
        return ProviderService._get_api_key_for_provider(provider)

    @staticmethod
    def validate_provider_config(
        provider: str,
        model: str,
        base_url: str | None = None,
    ) -> tuple[bool, str]:
        """Validate provider configuration.

        Args:
            provider: Provider identifier
            model: Model name
            base_url: Optional custom base URL

        Returns:
            Tuple of (is_valid, error_message)
        """
        config = PROVIDER_PRESETS.get(provider.lower())
        if not config:
            return False, f"Unknown provider: {provider}"

        # Model validation is permissive - allow any model name
        # Providers will return their own errors if model is invalid

        return True, ""

    @staticmethod
    def _get_client(provider: str, base_url: str | None = None) -> AsyncOpenAI:
        """Create an AsyncOpenAI client configured for the given provider.

        Args:
            provider: Provider identifier
            base_url: Optional override base URL

        Returns:
            Configured AsyncOpenAI client

        Raises:
            ValueError: If base URL validation fails
        """
        provider = provider.lower()
        api_key = ProviderService._get_api_key_for_provider(provider)
        config = PROVIDER_PRESETS.get(provider, {})

        # Determine base URL: explicit override > provider preset
        url = base_url or config.get("base_url")

        # Validate base URL if provided (skip validation for None/empty)
        if url:
            is_valid, error_msg = ProviderService._validate_base_url(url, provider)
            if not is_valid:
                raise ValueError(f"Invalid base URL: {error_msg}")

        # LM Studio requires /v1 suffix for OpenAI-compatible API
        # Auto-append if not already present
        if provider == "lmstudio" and url and not url.endswith("/v1"):
            url = url.rstrip("/") + "/v1"
            print(f"[LM Studio] Auto-appended /v1 to base URL: {url}")

        client_kwargs: Dict[str, Any] = {}
        if url:
            client_kwargs["base_url"] = url
        if api_key:
            client_kwargs["api_key"] = api_key
        else:
            # Some providers (e.g., LM Studio) may not need auth
            client_kwargs["api_key"] = "no-key"

        return AsyncOpenAI(**client_kwargs)

    @staticmethod
    async def create_embeddings(
        provider: str,
        model: str,
        texts: List[str],
        base_url: str | None = None,
    ) -> List[List[float]]:
        """Create embeddings using the specified provider.

        Args:
            provider: Provider identifier
            model: Embedding model name
            texts: List of texts to embed
            base_url: Optional override base URL

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        client = ProviderService._get_client(provider, base_url)

        # Log embedding request
        effective_url = base_url or PROVIDER_PRESETS.get(provider.lower(), {}).get("base_url", "default")
        print(f"[EMBEDDINGS] Provider: {provider} | Model: {model} | URL: {effective_url} | Texts: {len(texts)}")

        response = await client.embeddings.create(
            model=model,
            input=texts,
        )

        return [item.embedding for item in response.data]

    @staticmethod
    async def stream_chat_completion(
        provider: str,
        model: str,
        messages: List[Dict[str, Any]],
        base_url: str | None = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator:
        """Stream chat completion using the specified provider.

        Args:
            provider: Provider identifier
            model: Chat model name
            messages: Conversation messages
            base_url: Optional override base URL
            tools: Optional tool definitions
            temperature: Sampling temperature

        Yields:
            Stream chunks from the provider
        """
        client = ProviderService._get_client(provider, base_url)

        # Log chat request
        effective_url = base_url or PROVIDER_PRESETS.get(provider.lower(), {}).get("base_url", "default")
        print(f"[CHAT] Provider: {provider} | Model: {model} | URL: {effective_url} | Messages: {len(messages)} | Tools: {len(tools) if tools else 0}")

        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        stream = await client.chat.completions.create(**kwargs)
        async for chunk in stream:
            yield chunk


provider_service = ProviderService()
