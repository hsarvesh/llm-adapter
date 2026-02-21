"""
LLM Adapter — Multi-Format File Processing REST API

A FastAPI application that accepts common file types, extracts their content,
and sends it to any configured LLM provider for processing or conversion.
"""

import time
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from telemetry.logger import setup_logging
from telemetry.middleware import TelemetryMiddleware
from telemetry.metrics import metrics
from parsers.base import ParserRegistry
from parsers.text_parser import TextParser
from parsers.document_parser import DocumentParser
from parsers.spreadsheet_parser import SpreadsheetParser
from parsers.image_parser import ImageParser
from parsers.fallback_parser import FallbackParser
from llm.provider_factory import get_provider, get_all_providers
from models.schemas import (
    ProcessResponse,
    BatchProcessResponse,
    ConvertResponse,
    SupportedFormatsResponse,
    ProvidersResponse,
    ProviderInfo,
    HealthResponse,
    ErrorResponse,
    MetricsResponse,
)
from utils.file_utils import (
    validate_file_size,
    get_file_extension,
    get_file_category,
    validate_conversion_target,
    SUPPORTED_FORMATS,
    CONVERSION_TARGETS,
)
from utils.cache import get_cached_content, set_cached_content

import structlog

# Initialize logging
setup_logging()
logger = structlog.get_logger(__name__)

# ──────────────────────────────────────────────
# App Setup
# ──────────────────────────────────────────────

app = FastAPI(
    title="LLM Adapter",
    description=(
        "A multi-format file processing API that extracts content from "
        "various file types and sends it to any LLM provider for analysis, "
        "summarization, or conversion."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Telemetry
app.add_middleware(TelemetryMiddleware)

# ──────────────────────────────────────────────
# Parser Registry
# ──────────────────────────────────────────────

parser_registry = ParserRegistry()
parser_registry.register(TextParser())
parser_registry.register(DocumentParser())
parser_registry.register(SpreadsheetParser())
parser_registry.register(ImageParser())
parser_registry.set_fallback(FallbackParser())


# ──────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────

async def _extract_content(file_bytes: bytes, filename: str) -> str:
    """Extract text content from file, using cache when available."""
    # Check cache first
    cached = get_cached_content(file_bytes, filename)
    if cached is not None:
        return cached

    # Parse the file
    parser = parser_registry.get_parser(filename)
    if parser is None:
        raise HTTPException(
            status_code=415,
            detail=f"No parser available for file: {filename}",
        )

    content = parser.parse(file_bytes, filename)

    # Cache the result
    set_cached_content(file_bytes, filename, content)
    return content


async def _process_single_file(
    file: UploadFile,
    prompt: Optional[str],
    provider_name: Optional[str],
    system_prompt: Optional[str],
) -> ProcessResponse:
    """Process a single file: extract content → send to LLM → return response."""
    start_time = time.time()

    # Read file
    file_bytes = await file.read()
    filename = file.filename or "unknown"
    file_ext = get_file_extension(filename)

    # Validate file size
    size_error = validate_file_size(file_bytes, filename)
    if size_error:
        raise HTTPException(status_code=413, detail=size_error)

    # Extract content
    extracted_content = await _extract_content(file_bytes, filename)

    # Build prompt for LLM
    user_prompt = _build_user_prompt(extracted_content, prompt, filename)

    # Default system prompt
    if not system_prompt:
        system_prompt = (
            "You are a helpful assistant that analyzes file content. "
            "The user has uploaded a file and its extracted content is provided. "
            "Respond to their request based on the file content."
        )

    # Get LLM provider and generate response
    try:
        provider = get_provider(provider_name)
        llm_response = await provider.generate(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("llm_error", error=str(e), provider=provider_name or settings.active_provider)
        raise HTTPException(
            status_code=502,
            detail=f"LLM provider error: {str(e)}",
        )

    processing_time = (time.time() - start_time) * 1000

    # Record metrics
    tokens = llm_response.token_usage.get("total_tokens", 0) if llm_response.token_usage else 0
    metrics.record_request(
        latency_ms=processing_time,
        provider=llm_response.provider,
        file_type=file_ext,
        success=True,
        tokens=tokens,
    )

    return ProcessResponse(
        success=True,
        filename=filename,
        file_type=file_ext,
        file_size_bytes=len(file_bytes),
        extracted_content_preview=extracted_content[:500],
        llm_response=llm_response.content,
        provider=llm_response.provider,
        model=llm_response.model,
        processing_time_ms=round(processing_time, 2),
        token_usage=llm_response.token_usage,
    )


def _build_user_prompt(content: str, user_prompt: Optional[str], filename: str) -> str:
    """Build the final user prompt combining file content and user instructions."""
    parts = [f"File: {filename}\n\nExtracted Content:\n{content}"]
    if user_prompt:
        parts.append(f"\n\nUser Request:\n{user_prompt}")
    else:
        parts.append(
            "\n\nPlease analyze this file content and provide a helpful summary."
        )
    return "\n".join(parts)


# ──────────────────────────────────────────────
# API Endpoints
# ──────────────────────────────────────────────

@app.post("/process", response_model=ProcessResponse, tags=["Processing"])
async def process_file(
    file: UploadFile = File(..., description="File to process"),
    prompt: Optional[str] = Form(None, description="Optional prompt/question about the file"),
    provider: Optional[str] = Form(None, description="LLM provider to use (default: active provider)"),
    system_prompt: Optional[str] = Form(None, description="Custom system prompt"),
):
    """
    Upload a file, extract its content, and get an LLM response.

    Supports: PDF, DOCX, PPTX, XLSX, CSV, TXT, MD, JSON, XML, HTML, and images.
    Unidentified file types are handled gracefully with best-effort extraction.
    """
    return await _process_single_file(file, prompt, provider, system_prompt)


@app.post("/process/batch", response_model=BatchProcessResponse, tags=["Processing"])
async def process_batch(
    files: List[UploadFile] = File(..., description="Files to process"),
    prompt: Optional[str] = Form(None, description="Optional prompt for all files"),
    provider: Optional[str] = Form(None, description="LLM provider to use"),
    system_prompt: Optional[str] = Form(None, description="Custom system prompt"),
):
    """Upload and process multiple files in a single request."""
    results = []
    errors = []

    for file in files:
        try:
            result = await _process_single_file(file, prompt, provider, system_prompt)
            results.append(result)
        except HTTPException as e:
            errors.append({"filename": file.filename or "unknown", "error": e.detail})
            file_ext = get_file_extension(file.filename or "unknown")
            metrics.record_request(
                latency_ms=0,
                provider=provider or settings.active_provider,
                file_type=file_ext,
                success=False,
            )
        except Exception as e:
            errors.append({"filename": file.filename or "unknown", "error": str(e)})

    return BatchProcessResponse(
        success=len(errors) == 0,
        total_files=len(files),
        processed=len(results),
        failed=len(errors),
        results=results,
        errors=errors,
    )


@app.post("/convert", response_model=ConvertResponse, tags=["Conversion"])
async def convert_file(
    file: UploadFile = File(..., description="File to convert"),
    target_format: str = Form(..., description=f"Target format: {', '.join(CONVERSION_TARGETS)}"),
    provider: Optional[str] = Form(None, description="LLM provider to use"),
):
    """
    Convert file content to a different format using LLM.

    Supported targets: markdown, json, summary, csv, key_points, table, plain_text.
    """
    start_time = time.time()

    # Validate target format
    format_error = validate_conversion_target(target_format)
    if format_error:
        raise HTTPException(status_code=400, detail=format_error)

    # Read and validate file
    file_bytes = await file.read()
    filename = file.filename or "unknown"
    size_error = validate_file_size(file_bytes, filename)
    if size_error:
        raise HTTPException(status_code=413, detail=size_error)

    # Extract content
    extracted_content = await _extract_content(file_bytes, filename)
    file_ext = get_file_extension(filename)

    # Build conversion prompt
    conversion_prompts = {
        "markdown": "Convert the following content to well-formatted Markdown. Preserve all information, use proper headings, lists, and formatting.",
        "json": "Convert the following content to structured JSON format. Organize the data logically with appropriate keys and nested structures.",
        "summary": "Provide a comprehensive summary of the following content. Include all key points, findings, and important details.",
        "csv": "Convert the following content to CSV format. Identify tabular data and structure it with appropriate column headers.",
        "key_points": "Extract the key points from the following content as a structured bullet-point list. Prioritize the most important information.",
        "table": "Organize the following content into a well-structured table format. Use markdown table syntax.",
        "plain_text": "Convert the following content to clean plain text. Remove any formatting, special characters, and organize for readability.",
    }

    system_prompt = (
        "You are a document conversion assistant. Your task is to convert file content "
        "to the requested format accurately and completely. Preserve all meaningful information."
    )
    user_prompt = (
        f"{conversion_prompts.get(target_format.lower(), 'Convert to the requested format.')}\n\n"
        f"Source file: {filename}\n\n"
        f"Content:\n{extracted_content}"
    )

    # Get LLM response
    try:
        llm_provider = get_provider(provider)
        llm_response = await llm_provider.generate(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM provider error: {str(e)}")

    processing_time = (time.time() - start_time) * 1000

    tokens = llm_response.token_usage.get("total_tokens", 0) if llm_response.token_usage else 0
    metrics.record_request(
        latency_ms=processing_time,
        provider=llm_response.provider,
        file_type=file_ext,
        success=True,
        tokens=tokens,
    )

    return ConvertResponse(
        success=True,
        filename=filename,
        source_format=file_ext,
        target_format=target_format,
        converted_content=llm_response.content,
        provider=llm_response.provider,
        model=llm_response.model,
        processing_time_ms=round(processing_time, 2),
    )


@app.get("/supported-formats", response_model=SupportedFormatsResponse, tags=["Info"])
async def get_supported_formats():
    """List all supported file formats by category."""
    total = sum(len(exts) for exts in SUPPORTED_FORMATS.values())
    return SupportedFormatsResponse(formats=SUPPORTED_FORMATS, total_extensions=total)


@app.get("/providers", response_model=ProvidersResponse, tags=["Info"])
async def get_providers():
    """List all available LLM providers and their configuration status."""
    all_providers = get_all_providers()
    provider_list = []

    for name, prov in all_providers.items():
        provider_list.append(
            ProviderInfo(
                name=prov.provider_name,
                display_name=prov.display_name,
                is_configured=prov.is_configured(),
                is_active=(name == settings.active_provider),
                models=prov.get_available_models(),
            )
        )

    return ProvidersResponse(
        active_provider=settings.active_provider,
        providers=provider_list,
    )


@app.get("/health", response_model=HealthResponse, tags=["Info"])
async def health_check():
    """Health check with provider connectivity status."""
    provider_status = "unconfigured"
    try:
        provider = get_provider()
        provider_status = "configured"
    except ValueError as e:
        provider_status = f"error: {str(e)}"

    return HealthResponse(
        status="healthy",
        active_provider=settings.active_provider,
        provider_status=provider_status,
    )


@app.get("/metrics", response_model=MetricsResponse, tags=["Telemetry"])
async def get_metrics():
    """View telemetry metrics: latency, token usage, errors, and breakdowns."""
    return MetricsResponse(**metrics.get_metrics())


# ──────────────────────────────────────────────
# Error Handlers
# ──────────────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Custom error response format."""
    error_code = {
        400: "BAD_REQUEST",
        413: "FILE_TOO_LARGE",
        415: "UNSUPPORTED_FORMAT",
        422: "VALIDATION_ERROR",
        502: "LLM_PROVIDER_ERROR",
    }.get(exc.status_code, "UNKNOWN_ERROR")

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=str(exc.detail),
            error_code=error_code,
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Catch-all error handler."""
    logger.error("unhandled_error", error=str(exc), type=type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="An unexpected error occurred.",
            error_code="INTERNAL_ERROR",
            detail=str(exc),
        ).model_dump(),
    )


# ──────────────────────────────────────────────
# Startup
# ──────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    logger.info(
        "app_started",
        active_provider=settings.active_provider,
        model=settings.llm_model,
        max_file_size_mb=settings.max_file_size_mb,
    )
