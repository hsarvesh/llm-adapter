"""Parser for image files using OCR: EasyOCR (primary), pytesseract (fallback)."""

import io
import structlog

from parsers.base import BaseParser

logger = structlog.get_logger(__name__)

# Detect available OCR engines at import time
_easyocr_available = False
_tesseract_available = False

try:
    import easyocr
    _easyocr_available = True
except ImportError:
    pass

try:
    import pytesseract
    from PIL import Image
    # Quick check if tesseract binary is available
    try:
        pytesseract.get_tesseract_version()
        _tesseract_available = True
    except Exception:
        pass
except ImportError:
    pass


class ImageParser(BaseParser):
    """Handles image files using OCR for text extraction."""

    def __init__(self):
        self._easyocr_reader = None

    @property
    def supported_extensions(self) -> list[str]:
        return [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif", ".webp"]

    def parse(self, file_bytes: bytes, filename: str) -> str:
        """Extract text from image using best available OCR engine."""
        if _easyocr_available:
            return self._parse_easyocr(file_bytes, filename)
        elif _tesseract_available:
            return self._parse_tesseract(file_bytes, filename)
        else:
            logger.warning("no_ocr_engine", filename=filename)
            return (
                f"[Image file detected: {filename}]\n"
                f"No OCR engine is available. Install EasyOCR (pip install easyocr) "
                f"or Tesseract (pip install pytesseract + install Tesseract binary) "
                f"to enable text extraction from images.\n"
                f"File size: {len(file_bytes)} bytes"
            )

    def _parse_easyocr(self, file_bytes: bytes, filename: str) -> str:
        """Extract text using EasyOCR (no external dependencies needed)."""
        try:
            import easyocr

            if self._easyocr_reader is None:
                logger.info("initializing_easyocr")
                self._easyocr_reader = easyocr.Reader(["en"], verbose=False)

            results = self._easyocr_reader.readtext(file_bytes)

            if not results:
                return f"[Image: {filename}] No text detected in image."

            # Extract text with confidence scores
            lines = []
            for bbox, text, confidence in results:
                if confidence > 0.3:  # Filter low-confidence results
                    lines.append(text)

            result = "\n".join(lines)
            logger.info(
                "image_parsed_easyocr",
                filename=filename,
                detections=len(results),
                text_length=len(result),
            )
            return result if result.strip() else f"[Image: {filename}] No readable text detected."
        except Exception as e:
            logger.error("easyocr_error", filename=filename, error=str(e))
            # Try fallback
            if _tesseract_available:
                return self._parse_tesseract(file_bytes, filename)
            return f"[Error extracting text from image: {str(e)}]"

    def _parse_tesseract(self, file_bytes: bytes, filename: str) -> str:
        """Extract text using pytesseract + Pillow."""
        try:
            import pytesseract
            from PIL import Image

            image = Image.open(io.BytesIO(file_bytes))

            # Convert to RGB if necessary
            if image.mode not in ("L", "RGB"):
                image = image.convert("RGB")

            text = pytesseract.image_to_string(image).strip()

            logger.info(
                "image_parsed_tesseract",
                filename=filename,
                text_length=len(text),
            )
            return text if text else f"[Image: {filename}] No readable text detected."
        except Exception as e:
            logger.error("tesseract_error", filename=filename, error=str(e))
            return f"[Error extracting text from image: {str(e)}]"
