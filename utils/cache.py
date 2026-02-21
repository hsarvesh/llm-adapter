"""In-memory LRU cache for parsed file content."""

import hashlib
from typing import Optional
from cachetools import TTLCache
from config import settings
import structlog

logger = structlog.get_logger(__name__)

# Global cache instance
_cache = TTLCache(
    maxsize=settings.cache_max_size,
    ttl=settings.cache_ttl_seconds,
)


def _make_key(file_bytes: bytes, filename: str) -> str:
    """Generate a cache key from file content hash and filename."""
    content_hash = hashlib.md5(file_bytes).hexdigest()
    return f"{filename}:{content_hash}"


def get_cached_content(file_bytes: bytes, filename: str) -> Optional[str]:
    """
    Retrieve parsed content from cache if available.

    Returns:
        Cached content string, or None if not cached.
    """
    key = _make_key(file_bytes, filename)
    result = _cache.get(key)
    if result is not None:
        logger.info("cache_hit", filename=filename)
    return result


def set_cached_content(file_bytes: bytes, filename: str, content: str) -> None:
    """Store parsed content in the cache."""
    key = _make_key(file_bytes, filename)
    _cache[key] = content
    logger.info("cache_set", filename=filename, content_length=len(content))


def clear_cache() -> None:
    """Clear the entire cache."""
    _cache.clear()
    logger.info("cache_cleared")
