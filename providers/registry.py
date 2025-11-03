"""
Provider registry for creating and managing LLM provider instances.
"""
from typing import Dict, Type, Any, Tuple
from .base import LLMProvider
from ..config import ProviderConfig


class ProviderRegistry:
    """Registry for LLM provider adapters."""
    
    _providers: Dict[str, Type[LLMProvider]] = {}
    
    @classmethod
    def register(cls, name: str, provider_class: Type[LLMProvider]) -> None:
        """
        Register a provider adapter.
        
        Args:
            name: Provider name (e.g., 'openai', 'anthropic')
            provider_class: Provider class to register
        """
        cls._providers[name] = provider_class
    
    @classmethod
    def get(cls, name: str) -> Type[LLMProvider]:
        """
        Get a registered provider class.
        
        Args:
            name: Provider name
        
        Returns:
            Provider class
        
        Raises:
            ValueError: If provider is not registered
        """
        if name not in cls._providers:
            raise ValueError(
                f"Provider '{name}' not registered. "
                f"Available providers: {list(cls._providers.keys())}"
            )
        return cls._providers[name]
    
    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered provider names."""
        return list(cls._providers.keys())


def create_provider(config: ProviderConfig) -> LLMProvider:
    """
    Create a provider instance from configuration.
    
    Args:
        config: Provider configuration
    
    Returns:
        Initialized provider instance
    
    Raises:
        ValueError: If provider is not registered or config is invalid
    """
    provider_class = ProviderRegistry.get(config.provider_id)
    return provider_class(config)


def register_builtin_providers() -> None:
    """Register all built-in provider adapters."""
    from .openai import OpenAIProvider
    from .anthropic import AnthropicProvider
    from .gemini import GeminiProvider

    ProviderRegistry.register("openai", OpenAIProvider)
    ProviderRegistry.register("anthropic", AnthropicProvider)
    ProviderRegistry.register("gemini", GeminiProvider)


# Cache for provider instances
_provider_instances: Dict[str, Any] = {}


def resolve_model_and_provider(config, model_id: str):
    """
    Resolve model ID to (provider_instance, provider_name, model_name).

    Args:
        config: Global Config instance
        model_id: Model ID from request

    Returns:
        Tuple of (provider_instance, provider_name, model_name) or None
    """
    try:
        model_config = config.get_model(model_id)
    except ValueError:
        return None

    provider_name = model_config.provider
    model_name = model_config.model

    # Get or create provider instance
    if provider_name not in _provider_instances:
        try:
            provider_config = config.get_provider(provider_name)
            _provider_instances[provider_name] = create_provider(provider_config)
        except Exception:
            return None

    provider = _provider_instances[provider_name]
    return (provider, provider_name, model_name)

