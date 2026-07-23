"""
Excel Parser — pandas / openpyxl

Converts each worksheet into a markdown-formatted table and wraps
it in a ``PageData`` entry.
"""

from __future__ import annotations

import os

from .base import BaseParser, DocumentData, PageData
from .exceptions import ParsingInterruptedError


class ExcelParser(BaseParser):
    """Parse Excel workbooks (``.xlsx``, ``.xls``)."""

    def supported_extensions(self) -> list[str]:
        return [".xlsx", ".xls"]

    def parse(self, file_path: str) -> DocumentData:
        filename = os.path.basename(file_path)
        pages: list[PageData] = []
        full_text: list[str] = []

        try:
            import pandas as pd
        except ImportError:
            raise ParsingInterruptedError(
                "pandas is not installed; install it with `pip install pandas openpyxl`",
                file_path=file_path,
            )

        try:
            excel_file = pd.ExcelFile(file_path)
        except Exception as exc:
            # Return a minimal DocumentData so the pipeline can record the error
            return DocumentData(
                filename=filename,
                file_type="xlsx",
                text=f"Excel parsing error: {exc}",
                metadata={"parser": "pandas/openpyxl", "error": str(exc)},
                pages=[PageData(page_number=1, text=f"Error: {exc}", blocks=[])],
            )

        for sheet_idx, sheet_name in enumerate(excel_file.sheet_names):
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            df_cleaned = df.dropna(how="all")

            table_md = (
                df_cleaned.to_markdown(index=False) if not df_cleaned.empty else ""
            )
            sheet_text = f"Sheet: {sheet_name}\n\n{table_md}"

            full_text.append(sheet_text)
            pages.append(
                PageData(
                    page_number=sheet_idx + 1,
                    text=sheet_text,
                    blocks=[
                        {
                            "text": sheet_text,
                            "type": "table",
                            "sheet_name": sheet_name,
                            "rows": len(df_cleaned),
                            "columns": list(df_cleaned.columns),
                        }
                    ],
                    headings=[f"Sheet: {sheet_name}"],
                    is_ocr=False,
                )
            )

        combined = "\n\n".join(full_text)
        return DocumentData(
            filename=filename,
            file_type="xlsx",
            text=combined,
            metadata={"parser": "pandas/openpyxl", "sheet_count": len(pages)},
            pages=pages if pages else [PageData(page_number=1, text=combined, blocks=[])],
        )
