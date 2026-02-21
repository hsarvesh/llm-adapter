"""Parser for archive and compressed formats: ZIP, 7Z, RAR, TAR, GZ."""

import io
import zipfile
import tarfile
import gzip
import structlog
from parsers.base import BaseParser

logger = structlog.get_logger(__name__)


class ArchiveParser(BaseParser):
    """Handles compressed and archive files."""

    @property
    def supported_extensions(self) -> list[str]:
        return [".zip", ".7z", ".rar", ".tar", ".gz", ".p7m", ".sig"]

    def parse(self, file_bytes: bytes, filename: str) -> str:
        ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""

        if ext == ".zip":
            return self._parse_zip(file_bytes, filename)
        elif ext == ".tar" or filename.endswith(".tar.gz"):
            return self._parse_tar(file_bytes, filename)
        elif ext == ".gz" and not filename.endswith(".tar.gz"):
            return self._parse_gz(file_bytes, filename)
        elif ext == ".7z":
            return self._parse_7z(file_bytes, filename)
        elif ext == ".rar":
            return self._parse_rar(file_bytes, filename)
        elif ext in (".p7m", ".sig"):
            return self._parse_security_container(file_bytes, filename, ext)
        else:
            return f"[Unsupported archive format: {ext}]"

    def _parse_zip(self, file_bytes: bytes, filename: str) -> str:
        """List contents and preview text files in a ZIP archive."""
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                files = z.infolist()
                result = [f"[ZIP Archive: {filename}]", f"Total Files: {len(files)}\n", "--- File List ---"]
                
                for f in files:
                    size_kb = f.file_size / 1024
                    result.append(f"{f.filename} ({size_kb:.1f} KB)")

                # Try to extract content from small text files
                previews = []
                for f in files[:10]: # Check first 10 files
                    if f.file_size < 50000 and any(f.filename.endswith(ext) for ext in [".txt", ".md", ".json", ".xml", ".yaml", ".yml", ".sql", ".ini"]):
                        try:
                            with z.open(f) as content:
                                text = content.read().decode("utf-8", errors="replace")
                                previews.append(f"\n--- Preview: {f.filename} ---\n{text[:1000]}")
                                if len(text) > 1000: previews[-1] += "..."
                        except Exception:
                            continue
                
                if previews:
                    result.append("\n" + "\n".join(previews))
                
                logger.info("zip_parsed", filename=filename, files=len(files))
                return "\n".join(result)
        except Exception as e:
            return f"[Error parsing ZIP: {str(e)}]"

    def _parse_7z(self, file_bytes: bytes, filename: str) -> str:
        """List contents of a 7z archive."""
        try:
            import py7zr
            with py7zr.SevenZipFile(io.BytesIO(file_bytes), mode='r') as z:
                files = z.getnames()
                result = [f"[7z Archive: {filename}]", f"Total Files: {len(files)}\n", "--- File List ---"]
                result.extend(files)
                logger.info("7z_parsed", filename=filename, files=len(files))
                return "\n".join(result)
        except ImportError:
            return "[Error: py7zr library not installed]"
        except Exception as e:
            return f"[Error parsing 7z: {str(e)}]"

    def _parse_rar(self, file_bytes: bytes, filename: str) -> str:
        """List contents of a RAR archive."""
        try:
            import rarfile
            with rarfile.RarFile(io.BytesIO(file_bytes)) as r:
                files = r.namelist()
                result = [f"[RAR Archive: {filename}]", f"Total Files: {len(files)}\n", "--- File List ---"]
                result.extend(files)
                logger.info("rar_parsed", filename=filename, files=len(files))
                return "\n".join(result)
        except ImportError:
            return "[Error: rarfile library not installed]"
        except Exception as e:
            return f"[Error parsing RAR: {str(e)} (Note: rarfile requires unrar tool on system)]"

    def _parse_tar(self, file_bytes: bytes, filename: str) -> str:
        """List contents of a TAR archive."""
        try:
            with tarfile.open(fileobj=io.BytesIO(file_bytes)) as t:
                files = t.getnames()
                result = [f"[TAR Archive: {filename}]", f"Total Files: {len(files)}\n", "--- File List ---"]
                result.extend(files)
                return "\n".join(result)
        except Exception as e:
            return f"[Error parsing TAR: {str(e)}]"

    def _parse_gz(self, file_bytes: bytes, filename: str) -> str:
        """Decompress GZ and try to parse as text."""
        try:
            decompressed = gzip.decompress(file_bytes)
            try:
                text = decompressed.decode("utf-8")
                return f"[GZ Decompressed: {filename}]\n\n{text}"
            except UnicodeDecodeError:
                return f"[GZ Decompressed: {filename}] (Binary content, {len(decompressed)} bytes)"
        except Exception as e:
            return f"[Error parsing GZ: {str(e)}]"

    def _parse_security_container(self, file_bytes: bytes, filename: str, ext: str) -> str:
        """Extract metadata from signed/encrypted containers."""
        try:
            # CMS/PKCS#7 extraction (requires cryptography)
            from cryptography import x509
            from cryptography.hazmat.primitives import hashes
            
            result = [f"[Security Container: {filename}]", f"Extension: {ext}"]
            
            # This is a very basic check. Proper p7m parsing is complex.
            # We'll just report the file size and try to find any embedded certificates
            result.append(f"Size: {len(file_bytes)} bytes")
            result.append("Status: Encrypted or Signed (Metadata only)")
            
            logger.info("security_container_detected", filename=filename, extension=ext)
            return "\n".join(result)
        except Exception:
            return f"[{ext.upper()} File: {filename}] Encrypted or signed binary data ({len(file_bytes)} bytes)."
