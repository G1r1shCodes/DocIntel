"""
DocIntel Parser Base Layer

Defines the shared data model (DocumentData / PageData) and the
abstract contract (BaseParser) that every format-specific parser
must implement.

Usage
-----
Concrete parsers inherit from BaseParser, implement the abstract
methods, and are automatically registered when their module is
imported.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class PageData:
    """Structured data for a single page (or logical page) of a document."""

    page_number: int
    text: str
    blocks: list[dict[str, Any]] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)
    headings: list[str] = field(default_factory=list)
    is_ocr: bool = False
    page_width: float | None = None
    page_height: float | None = None


@dataclass
class DocumentData:
    """Standardised representation returned by every parser."""

    filename: str
    file_type: str
    text: str
    metadata: dict[str, Any]
    pages: list[PageData]


# ---------------------------------------------------------------------------
# Magic-byte helpers
# ---------------------------------------------------------------------------

_MAGIC_BYTES: dict[str, bytes] = {
    ".pdf": b"%PDF-",
    ".docx": b"PK\x03\x04",  # ZIP archive
    ".doc": b"PK\x03\x04",  # .docx only; older .doc is OLE (not handled)
    ".xlsx": b"PK\x03\x04",
    ".xls": b"\xd0\xcf\x11\xe0",  # OLE2 Compound Document
    ".png": b"\x89PNG\r\n\x1a\n",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".tiff": b"II\x2a\x00",  # Little-endian TIFF
    ".bmp": b"BM",
    ".webp": b"RIFF",  # NOTE: RIFF is shared with AVI/WAV; extension + this check
    # is sufficient since we already know the declared extension.
}


def _read_header(file_path: str, n: int = 32) -> bytes:
    """Safely read the first *n* bytes of a file."""
    with open(file_path, "rb") as f:
        return f.read(n)


def check_magic_bytes(file_path: str, extension: str) -> bool:
    """
    Verify that the file's header matches the expected magic bytes for the
    given extension. Returns ``True`` when no magic bytes are registered
    for the extension (i.e. plain text files).
    """
    expected = _MAGIC_BYTES.get(extension.lower())
    if expected is None:
        return True  # no known magic bytes – skip check
    header = _read_header(file_path, len(expected))
    return header.startswith(expected)


# ---------------------------------------------------------------------------
# Abstract base parser
# ---------------------------------------------------------------------------

# Module-level registry: extension → parser instance
_PARSER_REGISTRY: dict[str, BaseParser] = {}  # type: ignore[name-defined]  # forward ref


def _register(parser: BaseParser) -> None:
    """Register a parser for each of its supported extensions."""
    for ext in parser.supported_extensions():
        _PARSER_REGISTRY[ext.lower()] = parser


class BaseParser(ABC):
    """
    Abstract parser that every format parser must implement.

    Subclasses only need to implement :meth:`parse` and
    :meth:`supported_extensions`; :meth:`validate` can be overridden
    for custom header checks.
    """

    #: Environment variable that overrides the OCR timeout (seconds).
    OCR_TIMEOUT_ENV: ClassVar[str] = "DOCINTEL_OCR_TIMEOUT"

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Auto-register *direct* subclasses of :class:`BaseParser` on
        module import.  Grandchild classes (subclasses of concrete
        parsers) are ignored to avoid accidentally overwriting registry
        entries.
        """
        super().__init_subclass__(**kwargs)
        # Only auto-register direct children of BaseParser
        if BaseParser in cls.__bases__:
            instance = cls()
            _register(instance)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @staticmethod
    def read_header(file_path: str, n: int = 32) -> bytes:
        """Read the first *n* bytes of a file for validation."""
        return _read_header(file_path, n)

    @staticmethod
    def get_ocr_timeout() -> int:
        """Return the OCR timeout (seconds), overriding from env."""
        return int(os.environ.get(BaseParser.OCR_TIMEOUT_ENV, "5"))

    # ------------------------------------------------------------------
    # Abstract methods
    # ------------------------------------------------------------------

    @abstractmethod
    def parse(self, file_path: str) -> DocumentData:
        """Parse *file_path* and return a :class:`DocumentData` instance."""
        ...

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return the list of file extensions handled by this parser (e.g. ``['.pdf']``)."""
        ...

    # ------------------------------------------------------------------
    # Validation (override in subclasses for stricter checks)
    # ------------------------------------------------------------------

    def validate(self, file_path: str) -> bool:
        """
        Verify the file's header bytes match the expected format.

        Override when you need format-specific checks beyond magic bytes.
        """
        ext = os.path.splitext(file_path)[1].lower()
        return check_magic_bytes(file_path, ext)


# Re-export for downstream imports that used ``base_parser`` directly.
# The old module path is kept as a compatibility shim.
__all__ = [
    "BaseParser",
    "DocumentData",
    "PageData",
    "check_magic_bytes",
]
