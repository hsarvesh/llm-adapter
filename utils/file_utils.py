"""File type detection, validation, and size enforcement utilities."""

from typing import Optional
from config import settings
import structlog

logger = structlog.get_logger(__name__)

# Supported extensions grouped by category
SUPPORTED_FORMATS = {
    "Documents": [".pdf", ".docx", ".pptx"],
    "Spreadsheets": [".xlsx", ".xls"],
    "Text": [".txt", ".md"],
    "Web": [".html", ".htm"],
    "Data": [".json", ".xml", ".csv"],
    "Images": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif", ".webp"],
}

# Supported conversion target formats
CONVERSION_TARGETS = ["markdown", "json", "summary", "csv", "key_points", "table", "plain_text"]

# Flatten to a set for quick lookup
ALL_SUPPORTED_EXTENSIONS = {ext for exts in SUPPORTED_FORMATS.values() for ext in exts}


def get_file_extension(filename: str) -> str:
    """Extract lowercase file extension from a filename."""
    if "." in filename:
        return "." + filename.rsplit(".", 1)[-1].lower()
    return ""


def is_supported(filename: str) -> bool:
    """Check if the file type is natively supported."""
    return get_file_extension(filename) in ALL_SUPPORTED_EXTENSIONS


def validate_file_size(file_bytes: bytes, filename: str) -> Optional[str]:
    """
    Validate file size against the configured limit.

    Returns:
        None if valid, error message string if invalid.
    """
    size = len(file_bytes)
    max_bytes = settings.max_file_size_bytes

    if size > max_bytes:
        return (
            f"File '{filename}' ({size / (1024 * 1024):.1f} MB) exceeds the "
            f"maximum allowed size of {settings.max_file_size_mb} MB."
        )
    if size == 0:
        return f"File '{filename}' is empty (0 bytes)."
    return None


def detect_mime_type(file_bytes: bytes) -> str:
    """Detect MIME type using python-magic if available."""
    try:
        import magic
        return magic.from_buffer(file_bytes[:2048], mime=True)
    except Exception:
        return "application/octet-stream"


def get_file_category(filename: str) -> str:
    """Return the category name for a given file extension."""
    ext = get_file_extension(filename)
    for category, extensions in SUPPORTED_FORMATS.items():
        if ext in extensions:
            return category
    return "Unknown"


def validate_conversion_target(target_format: str) -> Optional[str]:
    """
    Validate conversion target format.

    Returns:
        None if valid, error message string if invalid.
    """
    if target_format.lower() not in CONVERSION_TARGETS:
        return (
            f"Unsupported conversion target '{target_format}'. "
            f"Supported targets: {', '.join(CONVERSION_TARGETS)}"
        )
    return None
