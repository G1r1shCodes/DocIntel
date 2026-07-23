"""
Plain-text Parser — TXT, MD, JSON, LOG

Reads plain-text files line-by-line. Detects Markdown headings
and treats each non-empty line as a paragraph block.
"""

from __future__ import annotations

import os

from .base import BaseParser, DocumentData, PageData
from .exceptions import ParsingInterruptedError


class TXTParser(BaseParser):
    """Parse plain text / markdown / log / json files."""

    #: We claim ``.*`` as a fallback extension so the factory can route
    #: unknown extensions here as a last resort.
    FALLBACK_EXTENSION = ".*"

    def supported_extensions(self) -> list[str]:
        return [".txt", ".md", ".json", ".log", self.FALLBACK_EXTENSION]

    def validate(self, file_path: str) -> bool:
        """Check the file is a readable text file (no binary garbage)."""
        try:
            with open(file_path, "rb") as f:
                raw = f.read(1024)
            raw.decode("utf-8")
            return True
        except (OSError, UnicodeDecodeError):
            return False

    def parse(self, file_path: str) -> DocumentData:
        filename = os.path.basename(file_path)

        try:
            with open(file_path, "r", encoding="utf-8", errors="strict") as f:
                text = f.read()
        except UnicodeDecodeError:
            # Fall back to lossy reading
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()

        lines = text.splitlines()
        blocks = [
            {"text": line, "type": "paragraph"}
            for line in lines
            if line.strip()
        ]
        headings = [
            line.lstrip("# ").strip()
            for line in lines
            if line.startswith("#")
        ]

        page = PageData(
            page_number=1,
            text=text,
            blocks=blocks,
            headings=headings,
            is_ocr=False,
        )

        return DocumentData(
            filename=filename,
            file_type=os.path.splitext(filename)[1].lstrip(".") or "txt",
            text=text,
            metadata={"parser": "text/utf-8", "line_count": len(lines)},
            pages=[page],
        )
