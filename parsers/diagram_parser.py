"""Parser for diagram formats: VSDX, Draw.io."""

import io
import zipfile
import structlog
from bs4 import BeautifulSoup

from parsers.base import BaseParser

logger = structlog.get_logger(__name__)


class DiagramParser(BaseParser):
    """Handles Visio (.vsdx) and Diagrams.net (.drawio, .dio) files."""

    @property
    def supported_extensions(self) -> list[str]:
        return [".vsdx", ".drawio", ".dio"]

    def parse(self, file_bytes: bytes, filename: str) -> str:
        ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""

        if ext == ".vsdx":
            return self._parse_vsdx(file_bytes, filename)
        elif ext in (".drawio", ".dio"):
            return self._parse_drawio(file_bytes, filename)
        else:
            return f"[Unsupported diagram format: {ext}]"

    def _parse_vsdx(self, file_bytes: bytes, filename: str) -> str:
        """Extract text from Visio .vsdx file (which is a ZIP of XML)."""
        try:
            pages_content = []
            
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                # Visio pages are in visio/pages/page[n].xml
                # Let's list files and find page XMLs
                page_files = sorted([f for f in z.namelist() if f.startswith("visio/pages/page") and f.endswith(".xml")])
                
                for i, page_file in enumerate(page_files):
                    with z.open(page_file) as p:
                        soup = BeautifulSoup(p.read(), "xml")
                        # Extract all text elements
                        texts = [t.get_text().strip() for t in soup.find_all("Text") if t.get_text().strip()]
                        
                        if texts:
                            pages_content.append(f"--- Page {i + 1} ({page_file}) ---\n" + "\n".join(texts))

            if not pages_content:
                # Try a broader search for any text-like tags in the entire zip
                return f"[Visio: {filename}] No text elements found in standard locations."

            result = "\n\n".join(pages_content)
            logger.info("vsdx_parsed", filename=filename, pages=len(pages_content))
            return result
        except zipfile.BadZipFile:
            logger.error("vsdx_invalid_zip", filename=filename)
            return "[Error: Invalid Visio file (not a valid ZIP archive)]"
        except Exception as e:
            logger.error("vsdx_parse_error", filename=filename, error=str(e))
            return f"[Error extracting Visio content: {str(e)}]"

    def _parse_drawio(self, file_bytes: bytes, filename: str) -> str:
        """Extract text from Draw.io / Diagrams.net XML file."""
        try:
            # Draw.io files are usually XML
            try:
                content = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                content = file_bytes.decode("utf-8", errors="replace")

            soup = BeautifulSoup(content, "xml")
            
            # Draw.io often stores text in 'value' attribute of cells
            cells = soup.find_all("mxCell")
            texts = []
            
            for cell in cells:
                val = cell.get("value")
                if val:
                    # Value might contain HTML, clean it
                    clean_text = BeautifulSoup(val, "html.parser").get_text().strip()
                    if clean_text:
                        texts.append(clean_text)

            # If no cells found, try regular text extraction
            if not texts:
                texts = [t.strip() for t in soup.stripped_strings if t.strip()]

            if not texts:
                return f"[Diagram: {filename}] No text content detected."

            result = "\n".join(texts)
            logger.info("drawio_parsed", filename=filename, elements=len(texts))
            return result
        except Exception as e:
            logger.error("drawio_parse_error", filename=filename, error=str(e))
            return f"[Error extracting Draw.io content: {str(e)}]"
