"""Provider factory — resolves provider name to configured client instance."""

from typing import Dict, Optional
import structlog

from llm.base import BaseLLMProvider
from llm.openai_client import OpenAIClient, AzureOpenAIClient, OllamaClient, CustomLLMClient
from llm.gemini_client import GeminiClient
from llm.anthropic_client import AnthropicClient
from llm.cohere_client import CohereClient
from llm.mistral_client import MistralClient
from llm.huggingface_client import HuggingFaceClient
from config import settings

logger = structlog.get_logger(__name__)

# Singleton registry of provider instances
_providers: Dict[str, BaseLLMProvider] = {}


def _init_providers() -> None:
    """Initialize all provider instances."""
    global _providers
    if _providers:
        return
    _providers = {
        "openai": OpenAIClient(),
        "gemini": GeminiClient(),
        "anthropic": AnthropicClient(),
        "cohere": CohereClient(),
        "mistral": MistralClient(),
        "huggingface": HuggingFaceClient(),
        "ollama": OllamaClient(),
        "azure": AzureOpenAIClient(),
        "custom": CustomLLMClient(),
    }


def get_provider(name: Optional[str] = None) -> BaseLLMProvider:
    """
    Get a provider by name.

    Args:
        name: Provider name. If None, returns the active provider from config.

    Returns:
        Configured BaseLLMProvider instance.

    Raises:
        ValueError: If the provider is unknown or not configured.
    """
    _init_providers()

    name = (name or settings.active_provider).lower().strip()

    if name not in _providers:
        available = ", ".join(_providers.keys())
        raise ValueError(
            f"Unknown provider '{name}'. Available providers: {available}"
        )

    provider = _providers[name]

    if not provider.is_configured():
        raise ValueError(
            f"Provider '{provider.display_name}' is not configured. "
            f"Please set the required environment variables. "
            f"See .env.example for details."
        )

    logger.info("provider_selected", provider=name, display_name=provider.display_name)
    return provider


def get_all_providers() -> Dict[str, BaseLLMProvider]:
    """Return all registered provider instances."""
    _init_providers()
    return _providers.copy()
