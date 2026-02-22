"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    content: str
    provider: str
    model: str
    token_usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None
    raw_response: Optional[dict] = field(default=None, repr=False)


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM provider implementations."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the canonical name of this provider."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Return a human-friendly display name."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the provider has valid credentials configured."""
        pass

    @abstractmethod
    async def generate(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        images: Optional[list[bytes]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            user_prompt: The user's input text (includes extracted file content).
            system_prompt: Optional system prompt for context setting.
            model: Model override (uses default from config if None).
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in the response.

        Returns:
            Standardized LLMResponse object.
        """
        pass

    @abstractmethod
    def get_available_models(self) -> list[str]:
        """Return list of known available models for this provider."""
        pass
