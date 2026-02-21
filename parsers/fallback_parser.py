"""Fallback parser for unidentified or unsupported file types."""

import structlog
from parsers.base import BaseParser

logger = structlog.get_logger(__name__)


class FallbackParser(BaseParser):
    """Handles unidentified or unsupported file types gracefully."""

    @property
    def supported_extensions(self) -> list[str]:
        # This parser doesn't register for specific extensions;
        # it's set as the fallback in the registry.
        return []

    def parse(self, file_bytes: bytes, filename: str) -> str:
        """
        Attempt to extract content from unidentified files.

        Strategy:
        1. Try UTF-8 decoding → return text content with warning
        2. Try Latin-1 decoding → return partial content
        3. Binary file → return metadata only
        """
        ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else "(no extension)"

        # Detect MIME type if python-magic is available
        mime_type = self._detect_mime(file_bytes)

        # Strategy 1: Try UTF-8 decode
        try:
            text = file_bytes.decode("utf-8")
            # Validate it looks like real text (not binary garbage)
            printable_ratio = sum(1 for c in text[:1000] if c.isprintable() or c in "\n\r\t") / max(len(text[:1000]), 1)
            if printable_ratio > 0.85:
                logger.info(
                    "fallback_utf8_success",
                    filename=filename,
                    extension=ext,
                    mime=mime_type,
                    length=len(text),
                )
                return (
                    f"[WARNING: Unrecognized file format '{ext}']\n"
                    f"[MIME type: {mime_type}]\n"
                    f"[Content extracted as plain text — accuracy not guaranteed]\n\n"
                    f"{text}"
                )
        except UnicodeDecodeError:
            pass

        # Strategy 2: Try Latin-1 (always succeeds but may have artifacts)
        try:
            text = file_bytes.decode("latin-1")
            printable_ratio = sum(1 for c in text[:1000] if c.isprintable() or c in "\n\r\t") / max(len(text[:1000]), 1)
            if printable_ratio > 0.7:
                # Truncate very long content
                preview = text[:5000]
                truncated = len(text) > 5000
                logger.info(
                    "fallback_latin1_success",
                    filename=filename,
                    extension=ext,
                    mime=mime_type,
                )
                result = (
                    f"[WARNING: Unrecognized file format '{ext}']\n"
                    f"[MIME type: {mime_type}]\n"
                    f"[Content extracted with Latin-1 encoding — may contain artifacts]\n\n"
                    f"{preview}"
                )
                if truncated:
                    result += f"\n\n[... truncated, total size: {len(text)} characters]"
                return result
        except Exception:
            pass

        # Strategy 3: Binary file — metadata only
        logger.warning(
            "fallback_binary_file",
            filename=filename,
            extension=ext,
            mime=mime_type,
            size=len(file_bytes),
        )
        return (
            f"[UNSUPPORTED FILE FORMAT]\n"
            f"Filename: {filename}\n"
            f"Extension: {ext}\n"
            f"MIME type: {mime_type}\n"
            f"File size: {len(file_bytes)} bytes ({len(file_bytes) / 1024:.1f} KB)\n\n"
            f"This file type cannot be parsed into text. "
            f"Supported formats include: PDF, DOCX, PPTX, XLSX, CSV, TXT, MD, "
            f"JSON, XML, HTML, Image formats, Visio (VSDX), Draw.io, "
            f"XER, PlantUML, MS Project (MPP), RTF, EML, MSG, ICS, VCF, "
            f"MHTML, OneNote, PST, SQLite, Parquet, and Archives (ZIP/7Z/RAR)."
        )

    def _detect_mime(self, file_bytes: bytes) -> str:
        """Detect MIME type using python-magic if available."""
        try:
            import magic
            return magic.from_buffer(file_bytes[:2048], mime=True)
        except Exception:
            return "unknown"
