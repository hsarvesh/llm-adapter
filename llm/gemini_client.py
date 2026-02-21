"""Google Gemini LLM client."""

from typing import Optional
import structlog

from config import settings
from llm.base import BaseLLMProvider, LLMResponse

logger = structlog.get_logger(__name__)


class GeminiClient(BaseLLMProvider):
    """Google Gemini API client."""

    def __init__(self):
        self._model = None

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def display_name(self) -> str:
        return "Google Gemini"

    def is_configured(self) -> bool:
        return bool(settings.google_api_key)

    async def generate(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        import google.generativeai as genai

        genai.configure(api_key=settings.google_api_key)

        model_name = model or settings.llm_model
        if not model_name.startswith("gemini"):
            model_name = "gemini-1.5-flash"

        gen_model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt,
        )

        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        response = gen_model.generate_content(
            user_prompt,
            generation_config=generation_config,
        )

        # Extract token usage if available
        usage = None
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = {
                "prompt_tokens": getattr(response.usage_metadata, "prompt_token_count", 0),
                "completion_tokens": getattr(response.usage_metadata, "candidates_token_count", 0),
                "total_tokens": getattr(response.usage_metadata, "total_token_count", 0),
            }

        return LLMResponse(
            content=response.text or "",
            provider=self.provider_name,
            model=model_name,
            token_usage=usage,
            finish_reason="stop",
        )

    def get_available_models(self) -> list[str]:
        return ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.0-pro"]
