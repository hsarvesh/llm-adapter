"""Anthropic Claude LLM client."""

from typing import Optional
import structlog

from config import settings
from llm.base import BaseLLMProvider, LLMResponse

logger = structlog.get_logger(__name__)


class AnthropicClient(BaseLLMProvider):
    """Anthropic Claude API client."""

    def __init__(self):
        self._client = None

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def display_name(self) -> str:
        return "Anthropic Claude"

    def is_configured(self) -> bool:
        return bool(settings.anthropic_api_key)

    def _get_client(self):
        if self._client is None:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
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
        if not model.startswith("claude"):
            model = "claude-3-5-sonnet-20241022"

        # Build content list (text + optional images)
        content = [{"type": "text", "text": user_prompt}]
        if images:
            import base64
            for img_bytes in images:
                base64_img = base64.b64encode(img_bytes).decode("utf-8")
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": base64_img,
                    },
                })

        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": content}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = await client.messages.create(**kwargs)

        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text

        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            }

        return LLMResponse(
            content=content,
            provider=self.provider_name,
            model=model,
            token_usage=usage,
            finish_reason=response.stop_reason,
        )

    def get_available_models(self) -> list[str]:
        return ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"]
