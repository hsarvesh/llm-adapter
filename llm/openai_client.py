"""OpenAI-compatible LLM client (also serves Azure, Ollama, and Custom providers)."""

from typing import Optional
import structlog
from openai import AsyncOpenAI

from config import settings
from llm.base import BaseLLMProvider, LLMResponse

logger = structlog.get_logger(__name__)


class OpenAIClient(BaseLLMProvider):
    """OpenAI API client."""

    def __init__(self, api_key: Optional[str] = None):
        self._client = None
        self._api_key = api_key

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def display_name(self) -> str:
        return "OpenAI"

    def is_configured(self) -> bool:
        return bool(settings.openai_api_key)

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self._api_key or settings.openai_api_key,
                base_url=settings.openai_base_url,
            )
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
        
        # Build user content (text + optional images)
        if not images:
            user_content = user_prompt
        else:
            import base64
            user_content = [{"type": "text", "text": user_prompt}]
            for img_bytes in images:
                base64_img = base64.b64encode(img_bytes).decode("utf-8")
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}
                })

        messages.append({"role": "user", "content": user_content})

        response = await client.chat.completions.create(
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
        return ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo", "o1", "o1-mini"]


class AzureOpenAIClient(BaseLLMProvider):
    """Azure OpenAI API client."""

    def __init__(self, api_key: Optional[str] = None, endpoint: Optional[str] = None):
        self._client = None
        self._api_key = api_key
        self._endpoint = endpoint

    @property
    def provider_name(self) -> str:
        return "azure"

    @property
    def display_name(self) -> str:
        return "Azure OpenAI"

    def is_configured(self) -> bool:
        return bool(settings.azure_openai_key and settings.azure_openai_endpoint)

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            from openai import AsyncAzureOpenAI
            self._client = AsyncAzureOpenAI(
                api_key=self._api_key or settings.azure_openai_key,
                azure_endpoint=self._endpoint or settings.azure_openai_endpoint,
                api_version="2024-02-01",
            )
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
        model = model or settings.azure_openai_deployment or settings.llm_model

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Build user content (text + optional images)
        if not images:
            user_content = user_prompt
        else:
            import base64
            user_content = [{"type": "text", "text": user_prompt}]
            for img_bytes in images:
                base64_img = base64.b64encode(img_bytes).decode("utf-8")
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}
                })

        messages.append({"role": "user", "content": user_content})

        response = await client.chat.completions.create(
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
        return ["(configured via Azure deployment)"]


class OllamaClient(BaseLLMProvider):
    """Ollama local LLM client (OpenAI-compatible API)."""

    def __init__(self, base_url: Optional[str] = None):
        self._client = None
        self._base_url = base_url

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def display_name(self) -> str:
        return "Ollama (Local)"

    def is_configured(self) -> bool:
        return bool(settings.ollama_base_url)

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key="ollama",  # Ollama doesn't need a real key
                base_url=self._base_url or settings.ollama_base_url,
            )
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

        # Note: Basic Ollama integration here doesn't support images yet in this implementation
        # but signature must match BaseLLMProvider

        response = await client.chat.completions.create(
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
        return ["llama3", "llama3.1", "mistral", "codellama", "phi3", "gemma2"]


class CustomLLMClient(BaseLLMProvider):
    """Custom OpenAI-compatible endpoint client."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self._client = None
        self._api_key = api_key
        self._base_url = base_url

    @property
    def provider_name(self) -> str:
        return "custom"

    @property
    def display_name(self) -> str:
        return "Custom Provider"

    def is_configured(self) -> bool:
        return bool(settings.custom_llm_url)

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self._api_key or settings.custom_llm_api_key or "custom",
                base_url=self._base_url or settings.custom_llm_url,
                default_headers=settings.custom_headers,
            )
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
        model = model or settings.custom_llm_model or settings.llm_model

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        response = await client.chat.completions.create(
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
        return ["(configured via CUSTOM_LLM_MODEL)"]
