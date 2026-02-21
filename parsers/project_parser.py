"""Parser for Microsoft Project formats: MPP, MPT."""

import re
import structlog
from parsers.base import BaseParser

logger = structlog.get_logger(__name__)


class ProjectParser(BaseParser):
    """Handles Microsoft Project (.mpp, .mpt) files."""

    @property
    def supported_extensions(self) -> list[str]:
        return [".mpp", ".mpt"]

    def parse(self, file_bytes: bytes, filename: str) -> str:
        """
        Extract text content from binary Microsoft Project files.
        Since .mpp is a proprietary format, we use a robust string extraction strategy.
        """
        try:
            # Strategy: Extract sequences of printable characters (similar to 'strings' command)
            # We look for sequences of 4 or more printable characters
            # This often captures task names, resource names, and notes.
            
            # Use regex to find printable sequences in binary
            # Filter for reasonably long strings to avoid garbage
            pattern = re.compile(rb'[\x20-\x7E]{4,}')
            matches = pattern.findall(file_bytes)
            
            strings = []
            for m in matches:
                try:
                    s = m.decode('ascii').strip()
                    # Filter out common binary artifacts or very low-value strings
                    if s and not s.startswith(('<?xml', '<mxfile', 'PK\x03\x04')):
                        strings.append(s)
                except UnicodeDecodeError:
                    continue

            if not strings:
                return f"[Project: {filename}] No readable text strings found in binary file."

            # Deduplicate while preserving order
            seen = set()
            unique_strings = []
            for s in strings:
                if s not in seen and len(s) > 2:
                    unique_strings.append(s)
                    seen.add(s)

            result = (
                f"[Microsoft Project File: {filename}]\n"
                f"[Extracted Metadata & Strings]\n\n" + 
                "\n".join(unique_strings[:1000]) # Limit to first 1000 strings for brevity
            )
            
            if len(unique_strings) > 1000:
                result += f"\n\n[... and {len(unique_strings) - 1000} more strings]"

            logger.info("mpp_strings_extracted", filename=filename, count=len(unique_strings))
            return result
        except Exception as e:
            logger.error("mpp_parse_error", filename=filename, error=str(e))
            return f"[Error extracting Microsoft Project content: {str(e)}]"
