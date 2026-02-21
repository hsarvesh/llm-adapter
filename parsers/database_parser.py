"""Parser for database and analytics formats: SQLite, Parquet."""

import io
import sqlite3
import tempfile
import os
import structlog
from parsers.base import BaseParser

logger = structlog.get_logger(__name__)


class DatabaseParser(BaseParser):
    """Handles SQLite databases and Parquet files."""

    @property
    def supported_extensions(self) -> list[str]:
        return [".db", ".sqlite", ".parquet"]

    def parse(self, file_bytes: bytes, filename: str) -> str:
        ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""

        if ext in (".db", ".sqlite"):
            return self._parse_sqlite(file_bytes, filename)
        elif ext == ".parquet":
            return self._parse_parquet(file_bytes, filename)
        else:
            return f"[Unsupported database format: {ext}]"

    def _parse_sqlite(self, file_bytes: bytes, filename: str) -> str:
        """Extract schema and sample data from SQLite database."""
        temp_db = None
        try:
            # SQLite needs a file on disk
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
                f.write(file_bytes)
                temp_db = f.name

            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()

            # Get list of tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()

            result = [f"[SQLite Database: {filename}]", f"Total Tables: {len(tables)}\n"]

            for table_name_tuple in tables:
                table_name = table_name_tuple[0]
                result.append(f"--- Table: {table_name} ---")
                
                # Get schema
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                col_names = [c[1] for c in columns]
                result.append(f"Columns: {', '.join(col_names)}")

                # Get sample data (first 5 rows)
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 5;")
                rows = cursor.fetchall()
                if rows:
                    result.append("Sample Data (first 5 rows):")
                    for row in rows:
                        result.append(str(row))
                else:
                    result.append("(Empty table)")
                result.append("")

            conn.close()
            logger.info("sqlite_parsed", filename=filename, tables=len(tables))
            return "\n".join(result)
        except Exception as e:
            logger.error("sqlite_parse_error", filename=filename, error=str(e))
            return f"[Error extracting SQLite content: {str(e)}]"
        finally:
            if temp_db and os.path.exists(temp_db):
                os.remove(temp_db)

    def _parse_parquet(self, file_bytes: bytes, filename: str) -> str:
        """Extract schema and summary from Parquet analytics file."""
        try:
            import pandas as pd
            
            # Read parquet from bytes
            df = pd.read_parquet(io.BytesIO(file_bytes))
            
            result = [
                f"[Parquet File: {filename}]",
                f"Rows: {len(df)}",
                f"Columns: {len(df.columns)}\n",
                "--- Schema ---",
                str(df.dtypes),
                "\n--- Sample Data (first 5 rows) ---",
                df.head(5).to_string(index=False),
                "\n--- Statistical Summary ---",
                df.describe().to_string()
            ]
            
            logger.info("parquet_parsed", filename=filename, rows=len(df))
            return "\n".join(result)
        except ImportError:
            return "[Error: pandas or pyarrow library not installed]"
        except Exception as e:
            logger.error("parquet_parse_error", filename=filename, error=str(e))
            return f"[Error extracting Parquet content: {str(e)}]"
