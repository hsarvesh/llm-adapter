"""Parser for note and archive formats: ONE, PST, RTF."""

import io
import re
import structlog
from parsers.base import BaseParser

logger = structlog.get_logger(__name__)


class NoteParser(BaseParser):
    """Handles OneNote, Outlook Archives, and Rich Text files."""

    @property
    def supported_extensions(self) -> list[str]:
        return [".one", ".pst", ".rtf"]

    def parse(self, file_bytes: bytes, filename: str) -> str:
        ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""

        if ext == ".rtf":
            return self._parse_rtf(file_bytes, filename)
        elif ext in (".one", ".pst"):
            return self._parse_binary_strings(file_bytes, filename, ext)
        else:
            return f"[Unsupported note format: {ext}]"

    def _parse_rtf(self, file_bytes: bytes, filename: str) -> str:
        """Extract text from Rich Text Format file."""
        try:
            from striprtf.striprtf import rtf_to_text
            content = file_bytes.decode("utf-8", errors="ignore")
            text = rtf_to_text(content)
            logger.info("rtf_parsed", filename=filename)
            return text
        except Exception as e:
            logger.error("rtf_parse_error", filename=filename, error=str(e))
            # Binary string extraction fallback
            return self._parse_binary_strings(file_bytes, filename, ".rtf")

    def _parse_binary_strings(self, file_bytes: bytes, filename: str, ext: str) -> str:
        """Fallback string extraction for proprietary binary formats."""
        try:
            # Extract sequences of 4+ printable characters
            pattern = re.compile(rb'[\x20-\x7E]{4,}')
            matches = pattern.findall(file_bytes)
            
            strings = []
            for m in matches:
                try:
                    s = m.decode('ascii').strip()
                    # Filter common low-value patterns
                    if len(s) > 3 and not s.startswith(('<', '{', '!', 'PK')):
                        strings.append(s)
                except UnicodeDecodeError:
                    continue

            if not strings:
                return f"[{ext} File: {filename}] No readable text extracted."

            # Filter and deduplicate
            unique_strings = []
            seen = set()
            for s in strings:
                if s not in seen:
                    unique_strings.append(s)
                    seen.add(s)

            result = f"[{ext.upper()} File Content Preview: {filename}]\n\n"
            result += "\n".join(unique_strings[:1000])
            
            if len(unique_strings) > 1000:
                result += f"\n\n[... {len(unique_strings) - 1000} more strings detected]"

            logger.info("binary_strings_extracted", filename=filename, extension=ext, count=len(unique_strings))
            return result
        except Exception as e:
            logger.error("binary_parse_error", filename=filename, error=str(e))
            return f"[Error parsing {ext} file: {str(e)}]"
