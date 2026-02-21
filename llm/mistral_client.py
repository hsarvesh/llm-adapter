"""Mistral AI LLM client."""

from typing import Optional
import structlog

from config import settings
from llm.base import BaseLLMProvider, LLMResponse

logger = structlog.get_logger(__name__)


class MistralClient(BaseLLMProvider):
    """Mistral AI API client."""

    def __init__(self):
        self._client = None

    @property
    def provider_name(self) -> str:
        return "mistral"

    @property
    def display_name(self) -> str:
        return "Mistral AI"

    def is_configured(self) -> bool:
        return bool(settings.mistral_api_key)

    def _get_client(self):
        if self._client is None:
            from mistralai import Mistral
            self._client = Mistral(api_key=settings.mistral_api_key)
        return self._client

    async def generate(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        client = self._get_client()
        model = model or settings.llm_model
        if "mistral" not in model and "pixtral" not in model and "codestral" not in model:
            model = "mistral-large-latest"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        response = await client.chat.complete_async(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        choice = response.choices[0]
        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return LLMResponse(
            content=choice.message.content or "",
            provider=self.provider_name,
            model=model,
            token_usage=usage,
            finish_reason=choice.finish_reason,
        )

    def get_available_models(self) -> list[str]:
        return ["mistral-large-latest", "mistral-medium-latest", "mistral-small-latest",
                "codestral-latest", "pixtral-large-latest"]
