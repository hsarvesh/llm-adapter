"""Parser for text-based file formats: TXT, MD, CSV, JSON, XML, HTML."""

import csv
import io
import json
import xml.etree.ElementTree as ET

import structlog
from bs4 import BeautifulSoup

from parsers.base import BaseParser

logger = structlog.get_logger(__name__)


class TextParser(BaseParser):
    """Handles plain text and structured text formats."""

    @property
    def supported_extensions(self) -> list[str]:
        return [
            ".txt", ".md", ".csv", ".json", ".xml", ".html", ".htm", 
            ".puml", ".plantuml", ".uml", ".xer", ".sql", ".srt", ".vtt",
            ".yaml", ".yml", ".ini", ".cfg", ".pem", ".cer", ".crt"
        ]

    def parse(self, file_bytes: bytes, filename: str) -> str:
        ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""

        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = file_bytes.decode("latin-1")
            except Exception:
                text = file_bytes.decode("utf-8", errors="replace")
            logger.warning("unicode_decode_fallback", filename=filename)

        if ext == ".csv":
            return self._parse_csv(text, filename)
        elif ext == ".xer":
            return self._parse_csv(text, filename, delimiter="\t")
        elif ext == ".json":
            return self._parse_json(text, filename)
        elif ext in (".yaml", ".yml"):
            return self._parse_yaml(text, filename)
        elif ext in (".ini", ".cfg"):
            return self._parse_ini(text, filename)
        elif ext == ".xml":
            return self._parse_xml(text, filename)
        elif ext in (".html", ".htm"):
            return self._parse_html(text, filename)
        elif ext in (".srt", ".vtt"):
            return self._parse_subtitles(text, filename)
        else:
            # .txt, .md, .sql, .puml, .pem etc are returned as-is
            logger.info("text_parsed", filename=filename, length=len(text))
            return text

    def _parse_yaml(self, text: str, filename: str) -> str:
        """Parse YAML and format as clean text/JSON-like structure."""
        try:
            import yaml
            data = yaml.safe_load(text)
            return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("yaml_parse_error", filename=filename, error=str(e))
            return text

    def _parse_ini(self, text: str, filename: str) -> str:
        """Parse INI/CFG files."""
        try:
            import configparser
            config = configparser.ConfigParser()
            config.read_string(text)
            result = []
            for section in config.sections():
                result.append(f"[{section}]")
                for key, value in config.items(section):
                    result.append(f"{key} = {value}")
                result.append("")
            return "\n".join(result)
        except Exception as e:
            logger.error("ini_parse_error", filename=filename, error=str(e))
            return text

    def _parse_subtitles(self, text: str, filename: str) -> str:
        """Clean up subtitle files by removing timestamps and indexes."""
        import re
        # Remove SRT indexes and timestamps
        # 1
        # 00:00:01,000 --> 00:00:04,000
        text = re.sub(r'^\d+\r?\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}', '', text, flags=re.MULTILINE)
        # Remove VTT headers and timestamps
        text = re.sub(r'WEBVTT', '', text)
        text = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}.*', '', text)
        
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)

    def _parse_csv(self, text: str, filename: str, delimiter: str = ",") -> str:
        """Convert CSV/TSV to a formatted table string."""
        try:
            reader = csv.reader(io.StringIO(text), delimiter=delimiter)
            rows = list(reader)
            if not rows:
                return "(Empty CSV file)"

            # Calculate column widths
            col_widths = [0] * len(rows[0])
            for row in rows:
                for i, cell in enumerate(row):
                    if i < len(col_widths):
                        col_widths[i] = max(col_widths[i], len(str(cell)))

            # Format as table
            lines = []
            for row_idx, row in enumerate(rows):
                formatted = " | ".join(
                    str(cell).ljust(col_widths[i]) if i < len(col_widths) else str(cell)
                    for i, cell in enumerate(row)
                )
                lines.append(formatted)
                if row_idx == 0:
                    separator = "-+-".join("-" * w for w in col_widths)
                    lines.append(separator)

            result = "\n".join(lines)
            logger.info("csv_parsed", filename=filename, rows=len(rows))
            return result
        except Exception as e:
            logger.error("csv_parse_error", filename=filename, error=str(e))
            return text  # Return raw text as fallback

    def _parse_json(self, text: str, filename: str) -> str:
        """Pretty-print JSON content."""
        try:
            data = json.loads(text)
            result = json.dumps(data, indent=2, ensure_ascii=False)
            logger.info("json_parsed", filename=filename)
            return result
        except json.JSONDecodeError as e:
            logger.error("json_parse_error", filename=filename, error=str(e))
            return text  # Return raw text as fallback

    def _parse_xml(self, text: str, filename: str) -> str:
        """Extract text content from XML."""
        try:
            root = ET.fromstring(text)
            lines = []
            self._walk_xml(root, lines, depth=0)
            result = "\n".join(lines)
            logger.info("xml_parsed", filename=filename, elements=len(lines))
            return result
        except ET.ParseError as e:
            logger.error("xml_parse_error", filename=filename, error=str(e))
            return text

    def _walk_xml(self, element: ET.Element, lines: list, depth: int) -> None:
        """Recursively walk XML tree and extract text."""
        indent = "  " * depth
        tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag
        text = (element.text or "").strip()
        tail = (element.tail or "").strip()

        if text:
            lines.append(f"{indent}{tag}: {text}")
        elif list(element):
            lines.append(f"{indent}{tag}:")

        for child in element:
            self._walk_xml(child, lines, depth + 1)

        if tail:
            lines.append(f"{indent}{tail}")

    def _parse_html(self, text: str, filename: str) -> str:
        """Extract readable text from HTML using BeautifulSoup."""
        try:
            soup = BeautifulSoup(text, "lxml")

            # Remove script and style elements
            for tag in soup(["script", "style", "meta", "link"]):
                tag.decompose()

            # Get text with reasonable spacing
            result = soup.get_text(separator="\n", strip=True)

            # Clean up excessive blank lines
            lines = [line.strip() for line in result.splitlines() if line.strip()]
            result = "\n".join(lines)

            logger.info("html_parsed", filename=filename, length=len(result))
            return result
        except Exception as e:
            logger.error("html_parse_error", filename=filename, error=str(e))
            return text
