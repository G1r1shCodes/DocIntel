"""
DocIntel Parser Exception Hierarchy

Provides granular typed exceptions so the ingestion pipeline
can distinguish between transient OCR failures, unsupported
file formats, and file integrity / validation problems.
"""


class ParserError(Exception):
    """Base exception for all document parsing errors."""
    def __init__(self, message: str, file_path: str | None = None):
        self.file_path = file_path
        super().__init__(message)


class UnsupportedFormatError(ParserError):
    """Raised when no parser is registered for a given file extension."""
    def __init__(self, extension: str, file_path: str | None = None):
        self.extension = extension
        super().__init__(
            f"No parser registered for extension '{extension}'",
            file_path=file_path,
        )


class FileValidationError(ParserError):
    """Raised when magic-byte or header validation fails."""
    def __init__(self, expected: str, actual: str, file_path: str | None = None):
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"File validation failed: expected {expected}, got {actual[:20]!r}",
            file_path=file_path,
        )


class OCRError(ParserError):
    """Raised when Tesseract OCR fails or times out."""
    def __init__(self, message: str = "OCR processing failed", file_path: str | None = None):
        super().__init__(message, file_path=file_path)


class ParsingInterruptedError(ParserError):
    """Raised when parsing could not complete but partial DocumentData may exist."""
    def __init__(self, message: str, file_path: str | None = None):
        super().__init__(message, file_path=file_path)
