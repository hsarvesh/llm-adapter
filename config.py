"""Centralized application configuration loaded from environment variables."""

import json
from typing import Optional, Dict
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    # Active LLM Provider
    active_provider: str = Field(default="openai", description="Active LLM provider name")
    llm_model: str = Field(default="gpt-4o-mini", description="LLM model to use")

    # OpenAI
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"

    # Google Gemini
    google_api_key: Optional[str] = None

    # Anthropic
    anthropic_api_key: Optional[str] = None

    # Cohere
    cohere_api_key: Optional[str] = None

    # Mistral
    mistral_api_key: Optional[str] = None

    # HuggingFace
    hf_api_token: Optional[str] = None

    # Azure OpenAI
    azure_openai_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_openai_deployment: Optional[str] = None

    # Ollama (local)
    ollama_base_url: str = "http://localhost:11434/v1"

    # Custom Provider
    custom_llm_url: Optional[str] = None
    custom_llm_api_key: Optional[str] = None
    custom_llm_headers: str = "{}"
    custom_llm_model: Optional[str] = None

    # App Settings
    max_file_size_mb: int = 50
    cache_ttl_seconds: int = 300
    cache_max_size: int = 100
    log_level: str = "INFO"

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def custom_headers(self) -> Dict[str, str]:
        try:
            return json.loads(self.custom_llm_headers)
        except (json.JSONDecodeError, TypeError):
            return {}

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
