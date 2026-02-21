"""Pydantic request/response models for the LLM Adapter API."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ProcessResponse(BaseModel):
    """Response from the /process endpoint."""
    success: bool
    filename: str
    file_type: str
    file_size_bytes: int
    extracted_content_preview: str = Field(
        description="First 500 chars of extracted content"
    )
    llm_response: str
    provider: str
    model: str
    processing_time_ms: float
    token_usage: Optional[Dict[str, int]] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class BatchProcessResponse(BaseModel):
    """Response from the /process/batch endpoint."""
    success: bool
    total_files: int
    processed: int
    failed: int
    results: List[ProcessResponse]
    errors: List[Dict[str, str]] = []
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ConvertResponse(BaseModel):
    """Response from the /convert endpoint."""
    success: bool
    filename: str
    source_format: str
    target_format: str
    converted_content: str
    provider: str
    model: str
    processing_time_ms: float
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class SupportedFormatsResponse(BaseModel):
    """Response listing all supported file formats."""
    formats: Dict[str, List[str]]
    total_extensions: int


class ProviderInfo(BaseModel):
    """Information about an LLM provider."""
    name: str
    display_name: str
    is_configured: bool
    is_active: bool
    models: List[str] = []


class ProvidersResponse(BaseModel):
    """Response listing all available LLM providers."""
    active_provider: str
    providers: List[ProviderInfo]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    active_provider: str
    provider_status: str
    version: str = "1.0.0"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ErrorResponse(BaseModel):
    """Structured error response."""
    success: bool = False
    error: str
    error_code: str
    detail: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class MetricsResponse(BaseModel):
    """Telemetry metrics response."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    requests_by_provider: Dict[str, int]
    requests_by_file_type: Dict[str, int]
    total_tokens_used: int
    uptime_seconds: float
