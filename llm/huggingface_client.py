"""HuggingFace Inference API LLM client."""

from typing import Optional
import structlog

from config import settings
from llm.base import BaseLLMProvider, LLMResponse

logger = structlog.get_logger(__name__)


class HuggingFaceClient(BaseLLMProvider):
    """HuggingFace Inference API client."""

    def __init__(self):
        self._client = None

    @property
    def provider_name(self) -> str:
        return "huggingface"

    @property
    def display_name(self) -> str:
        return "HuggingFace"

    def is_configured(self) -> bool:
        return bool(settings.hf_api_token)

    def _get_client(self):
        if self._client is None:
            from huggingface_hub import AsyncInferenceClient
            self._client = AsyncInferenceClient(token=settings.hf_api_token)
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

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        response = await client.chat_completion(
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
                "total_tokens": response.usage.prompt_tokens + response.usage.completion_tokens,
            }

        return LLMResponse(
            content=choice.message.content or "",
            provider=self.provider_name,
            model=model,
            token_usage=usage,
            finish_reason=choice.finish_reason,
        )

    def get_available_models(self) -> list[str]:
        return [
            "meta-llama/Llama-3.1-70B-Instruct",
            "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "microsoft/Phi-3-mini-4k-instruct",
            "google/gemma-2-9b-it",
        ]
