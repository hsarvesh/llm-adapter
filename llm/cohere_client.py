"""Cohere LLM client."""

from typing import Optional
import structlog

from config import settings
from llm.base import BaseLLMProvider, LLMResponse

logger = structlog.get_logger(__name__)


class CohereClient(BaseLLMProvider):
    """Cohere API client."""

    def __init__(self):
        self._client = None

    @property
    def provider_name(self) -> str:
        return "cohere"

    @property
    def display_name(self) -> str:
        return "Cohere"

    def is_configured(self) -> bool:
        return bool(settings.cohere_api_key)

    def _get_client(self):
        if self._client is None:
            import cohere
            self._client = cohere.AsyncClientV2(api_key=settings.cohere_api_key)
        return self._client

    async def generate(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        images: Optional[list[bytes]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        client = self._get_client()
        model = model or settings.llm_model
        if not model.startswith("command"):
            model = "command-r-plus"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        response = await client.chat(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        content = ""
        if response.message and response.message.content:
            for block in response.message.content:
                if hasattr(block, "text"):
                    content += block.text

        usage = None
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": getattr(response.usage.tokens, "input_tokens", 0),
                "completion_tokens": getattr(response.usage.tokens, "output_tokens", 0),
                "total_tokens": (
                    getattr(response.usage.tokens, "input_tokens", 0)
                    + getattr(response.usage.tokens, "output_tokens", 0)
                ),
            }

        return LLMResponse(
            content=content,
            provider=self.provider_name,
            model=model,
            token_usage=usage,
            finish_reason=getattr(response, "finish_reason", "stop"),
        )

    def get_available_models(self) -> list[str]:
        return ["command-r-plus", "command-r", "command-light", "command"]
