"""Abstract base parser and parser registry for file content extraction."""

from abc import ABC, abstractmethod
from typing import Dict, Type, Optional
import structlog

logger = structlog.get_logger(__name__)


class BaseParser(ABC):
    """Abstract base class for all file parsers."""

    @abstractmethod
    def parse(self, file_bytes: bytes, filename: str) -> str:
        """
        Extract text content from file bytes.

        Args:
            file_bytes: Raw bytes of the uploaded file.
            filename: Original filename (used for extension detection).

        Returns:
            Extracted text content as a string.
        """
        pass

    def parse_rich(self, file_bytes: bytes, filename: str) -> tuple[str, Optional[list[bytes]]]:
        """
        Extract rich content (text and images) from file bytes.
        By default, returns text from parse() and no images.
        """
        return self.parse(file_bytes, filename), None

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions (e.g., ['.pdf', '.docx'])."""
        pass


class ParserRegistry:
    """Registry that maps file extensions to their parser implementations."""

    def __init__(self):
        self._parsers: Dict[str, BaseParser] = {}
        self._fallback_parser: Optional[BaseParser] = None

    def register(self, parser: BaseParser) -> None:
        """Register a parser for its supported extensions."""
        for ext in parser.supported_extensions:
            ext_lower = ext.lower()
            self._parsers[ext_lower] = parser
            logger.info("parser_registered", extension=ext_lower, parser=type(parser).__name__)

    def set_fallback(self, parser: BaseParser) -> None:
        """Set the fallback parser for unidentified file types."""
        self._fallback_parser = parser
        logger.info("fallback_parser_set", parser=type(parser).__name__)

    def get_parser(self, filename: str) -> Optional[BaseParser]:
        """Get the appropriate parser for a given filename."""
        ext = self._get_extension(filename)
        parser = self._parsers.get(ext)
        if parser:
            return parser
        if self._fallback_parser:
            logger.warning("using_fallback_parser", filename=filename, extension=ext)
            return self._fallback_parser
        return None

    def get_supported_formats(self) -> Dict[str, list[str]]:
        """Return supported formats grouped by category."""
        categories: Dict[str, list[str]] = {}
        for ext, parser in self._parsers.items():
            category = type(parser).__name__.replace("Parser", "")
            if category not in categories:
                categories[category] = []
            if ext not in categories[category]:
                categories[category].append(ext)
        return categories

    def is_supported(self, filename: str) -> bool:
        """Check if a file type is natively supported (not via fallback)."""
        ext = self._get_extension(filename)
        return ext in self._parsers

    @staticmethod
    def _get_extension(filename: str) -> str:
        """Extract lowercase file extension from filename."""
        if "." in filename:
            return "." + filename.rsplit(".", 1)[-1].lower()
        return ""
