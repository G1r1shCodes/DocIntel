"""
CSV Parser — pandas with BOM detection

Reads CSV files using pandas and renders them as markdown tables.
Falls back to raw text when pandas is unavailable.
"""

from __future__ import annotations

import os

from .base import BaseParser, DocumentData, PageData
from .exceptions import ParsingInterruptedError


class CSVParser(BaseParser):
    """Parse comma-separated value files."""

    #: UTF-8 BOM
    _BOM = b"\xef\xbb\xbf"

    def supported_extensions(self) -> list[str]:
        return [".csv"]

    def validate(self, file_path: str) -> bool:
        """Accept CSV even without magic bytes (just check it's readable)."""
        return os.path.isfile(file_path) and os.path.getsize(file_path) > 0

    def parse(self, file_path: str) -> DocumentData:
        filename = os.path.basename(file_path)
        content: str
        rows_count = 0
        cols: list[str] = []

        try:
            import pandas as pd
        except ImportError:
            raise ParsingInterruptedError(
                "pandas is not installed; install it with `pip install pandas`",
                file_path=file_path,
            )

        try:
            # Detect BOM encoding
            with open(file_path, "rb") as f:
                raw = f.read(4)
            encoding = "utf-8-sig" if raw.startswith(self._BOM) else "utf-8"

            df = pd.read_csv(file_path, encoding=encoding)
            df_cleaned = df.dropna(how="all")
            table_md = (
                df_cleaned.to_markdown(index=False) if not df_cleaned.empty else ""
            )
            content = f"CSV File: {filename}\n\n{table_md}"
            rows_count = len(df_cleaned)
            cols = list(df_cleaned.columns)
        except Exception:
            # Raw text fallback
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            rows_count = len(content.splitlines())

        page = PageData(
            page_number=1,
            text=content,
            blocks=[
                {
                    "text": content,
                    "type": "table",
                    "rows": rows_count,
                    "columns": cols,
                }
            ],
            headings=[filename],
            is_ocr=False,
        )

        return DocumentData(
            filename=filename,
            file_type="csv",
            text=content,
            metadata={"parser": "pandas/csv", "rows": rows_count},
            pages=[page],
        )
