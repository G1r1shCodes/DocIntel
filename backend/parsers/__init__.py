"""
DocIntel Parser Registry
========================

Unified entrypoint for multi-format document parsing with automatic
parser discovery and registration.

Usage
-----
>>> from parsers import parse_document
>>> doc = parse_document("report.pdf")
"""

from __future__ import annotations

import os

# Import the base classes so they are available as ``parsers.BaseParser`` etc.
from .base import (
    BaseParser,
    DocumentData,
    PageData,
    _PARSER_REGISTRY,
    _register,
    check_magic_bytes,
)
from .exceptions import (
    FileValidationError,
    OCRError,
    ParserError,
    ParsingInterruptedError,
    UnsupportedFormatError,
)

# ---------------------------------------------------------------------------
# Auto-import concrete parsers so their ``__init_subclass__`` hook runs.
# ---------------------------------------------------------------------------
from . import pdf_parser  # noqa: F401
from . import docx_parser  # noqa: F401
from . import excel_parser  # noqa: F401
from . import csv_parser  # noqa: F401
from . import image_parser  # noqa: F401
from . import txt_parser  # noqa: F401

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    # Factory
    "parse_document",
    # Data models
    "DocumentData",
    "PageData",
    "BaseParser",
    # Exceptions
    "ParserError",
    "UnsupportedFormatError",
    "FileValidationError",
    "OCRError",
    "ParsingInterruptedError",
    # Utilities
    "check_magic_bytes",
    "get_registered_parsers",
]


def get_registered_parsers() -> dict[str, BaseParser]:
    """Return a copy of the current extension → parser mapping."""
    return dict(_PARSER_REGISTRY)


def parse_document(file_path: str) -> DocumentData:
    """
    Route *file_path* to the correct parser, validate magic bytes,
    parse, and return a :class:`DocumentData` instance.

    Raises
    ------
    UnsupportedFormatError
        If no parser is registered for the file's extension.
    FileValidationError
        If the file header / magic bytes don't match the expected format.
    """
    ext = os.path.splitext(file_path)[1].lower()

    parser = _PARSER_REGISTRY.get(ext)
    if parser is None:
        # Last resort: try the generic fallback
        parser = _PARSER_REGISTRY.get(".*")

    if parser is None:
        raise UnsupportedFormatError(
            extension=ext or "(no extension)",
            file_path=file_path,
        )

    # Validate before parsing
    if not parser.validate(file_path):
        raise FileValidationError(
            expected=f"magic bytes for {ext}",
            actual=parser.read_header(file_path).decode("latin-1"),
            file_path=file_path,
        )

    return parser.parse(file_path)
