"""
Tests for the DocIntel Parser Layer
=====================================

Tests cover:
- BaseParser abstract contract
- Magic-byte validation
- All 6 concrete parsers (PDF, DOCX, XLSX, CSV, Image, TXT)
- Exception hierarchy
- Registry / factory pattern
"""

from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path

import pytest

from parsers import (
    BaseParser,
    DocumentData,
    FileValidationError,
    PageData,
    ParserError,
    UnsupportedFormatError,
    check_magic_bytes,
    get_registered_parsers,
    parse_document,
)
from parsers.base import _MAGIC_BYTES


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_pdf() -> Path:
    """Create a minimal valid PDF with a text page."""
    content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 44>>stream
BT /F1 12 Tf 100 700 Td (Hello World) Tj ET
endstream
endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
xref
0 6
...
trailer<</Size 6/Root 1 0 R>>
startxref
100
%%EOF"""
    p = Path(tempfile.mktemp(suffix=".pdf"))
    p.write_bytes(content)
    yield p
    p.unlink(missing_ok=True)


@pytest.fixture
def sample_docx() -> Path:
    """Create a minimal valid DOCX including required OPC parts."""
    import zipfile

    p = Path(tempfile.mktemp(suffix=".docx"))
    with zipfile.ZipFile(str(p), "w") as zf:
        zf.writestr(
            "[Content_Types].xml",
            b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>""",
        )
        zf.writestr(
            "_rels/.rels",
            b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>""",
        )
        zf.writestr(
            "word/document.xml",
            b"""<?xml version="1.0"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Hello from DOCX</w:t></w:r></w:p>
  </w:body>
</w:document>""",
        )
        zf.writestr(
            "word/_rels/document.xml.rels",
            b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>
""",
        )
    yield p
    p.unlink(missing_ok=True)


@pytest.fixture
def sample_csv() -> Path:
    content = b"name,value\nfoo,1\nbar,2\n"
    p = Path(tempfile.mktemp(suffix=".csv"))
    p.write_bytes(content)
    yield p
    p.unlink(missing_ok=True)


@pytest.fixture
def sample_txt() -> Path:
    content = b"# Heading 1\n\nSome paragraph text.\n"
    p = Path(tempfile.mktemp(suffix=".txt"))
    p.write_bytes(content)
    yield p
    p.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Test: Registry
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_parsers_are_registered(self):
        """All expected parsers are present after importing parsers."""
        registry = get_registered_parsers()
        assert ".pdf" in registry
        assert ".docx" in registry
        assert ".xlsx" in registry
        assert ".csv" in registry
        assert ".png" in registry
        assert ".txt" in registry
        assert ".*" in registry  # fallback

    def test_all_parsers_are_baseparser_instances(self):
        registry = get_registered_parsers()
        for ext, parser in registry.items():
            assert isinstance(parser, BaseParser), f"{ext} parser not a BaseParser"

    def test_parse_document_no_magic_bytes_fails(self):
        """File with .jpg extension but non-image content fails validation."""
        f = tempfile.NamedTemporaryFile(suffix=".jpg", mode="wb", delete=False)
        f.write(b"This is not a JPEG file")
        f.close()
        try:
            with pytest.raises(FileValidationError):
                parse_document(f.name)
        finally:
            os.unlink(f.name)


# ---------------------------------------------------------------------------
# Test: Magic bytes
# ---------------------------------------------------------------------------

class TestMagicBytes:
    def test_pdf_magic(self):
        """Valid PDF header passes magic-byte check."""
        f = tempfile.NamedTemporaryFile(suffix=".pdf", mode="wb", delete=False)
        f.write(b"%PDF-1.4")
        f.close()
        try:
            assert check_magic_bytes(f.name, ".pdf")
        finally:
            os.unlink(f.name)

    def test_pdf_rejected(self):
        """A text file with .pdf extension should fail magic-byte check."""
        f = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        f.write(b"This is not a PDF")
        f.close()
        try:
            assert not check_magic_bytes(f.name, ".pdf")
        finally:
            os.unlink(f.name)

    def test_png_magic(self):
        """Valid PNG header passes."""
        f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        f.write(b"\x89PNG\r\n\x1a\n...")
        f.close()
        try:
            assert check_magic_bytes(f.name, ".png")
        finally:
            os.unlink(f.name)

    def test_jpeg_magic(self):
        f = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        f.write(b"\xff\xd8\xff\xe0...")
        f.close()
        try:
            assert check_magic_bytes(f.name, ".jpg")
        finally:
            os.unlink(f.name)

    def test_docx_magic(self):
        """DOCX is a ZIP file, must start with PK\x03\x04."""
        import zipfile

        f = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
        with zipfile.ZipFile(f, "w") as zf:
            zf.writestr("word/document.xml", b"<d/>")
        f.close()
        try:
            assert check_magic_bytes(f.name, ".docx")
        finally:
            os.unlink(f.name)

    def test_txt_no_magic_check(self):
        """Plain-text extensions always pass magic-byte check."""
        f = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
        f.write(b"# Any content")
        f.close()
        try:
            assert check_magic_bytes(f.name, ".txt")
        finally:
            os.unlink(f.name)

    def test_magic_bytes_table_entries(self):
        """Every entry in _MAGIC_BYTES is at least 2 bytes long."""
        for ext, magic in _MAGIC_BYTES.items():
            assert len(magic) >= 2, f"{ext} has too-short magic bytes"


# ---------------------------------------------------------------------------
# Test: BaseParser contract
# ---------------------------------------------------------------------------

class TestBaseParserContract:
    def test_abstract_methods(self):
        """Cannot instantiate BaseParser directly."""
        with pytest.raises(TypeError):
            BaseParser()  # type: ignore

    def test_concrete_must_implement(self):
        """A subclass without abstract methods fails instantiation."""
        with pytest.raises(TypeError):

            class Incomplete(BaseParser):
                pass

            Incomplete()


# ---------------------------------------------------------------------------
# Test: PDF Parser
# ---------------------------------------------------------------------------

class TestPDFParser:
    def test_parse_pdf(self, sample_pdf):
        doc = parse_document(str(sample_pdf))
        assert isinstance(doc, DocumentData)
        assert doc.file_type == "pdf"
        assert doc.filename.endswith(".pdf")
        assert len(doc.pages) >= 1
        assert doc.text

    def test_parse_pdf_metadata(self, sample_pdf):
        doc = parse_document(str(sample_pdf))
        assert "page_count" in doc.metadata
        assert "parser" in doc.metadata

    def test_pdf_page_dimensions(self, sample_pdf):
        doc = parse_document(str(sample_pdf))
        for page in doc.pages:
            if page.page_width is not None:
                assert page.page_width > 0
            if page.page_height is not None:
                assert page.page_height > 0

    def test_pdf_fails_on_bogus_file(self):
        f = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        f.write(b"not a pdf")
        f.close()
        with pytest.raises(FileValidationError):
            parse_document(f.name)
        os.unlink(f.name)


# ---------------------------------------------------------------------------
# Test: DOCX Parser
# ---------------------------------------------------------------------------

class TestDOCXParser:
    def test_parse_docx(self, sample_docx):
        doc = parse_document(str(sample_docx))
        assert doc.file_type == "docx"
        assert "Hello from DOCX" in doc.text

    def test_docx_fails_on_non_zip(self):
        f = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
        f.write(b"not a zip file")
        f.close()
        with pytest.raises(FileValidationError):
            parse_document(f.name)
        os.unlink(f.name)


# ---------------------------------------------------------------------------
# Test: CSV Parser
# ---------------------------------------------------------------------------

class TestCSVParser:
    def test_parse_csv(self, sample_csv):
        doc = parse_document(str(sample_csv))
        assert doc.file_type == "csv"
        assert "name" in doc.text and "value" in doc.text
        assert "foo" in doc.text
        assert doc.metadata.get("rows") >= 2

    def test_csv_blocks_are_tables(self, sample_csv):
        doc = parse_document(str(sample_csv))
        for page in doc.pages:
            for block in page.blocks:
                assert block.get("type") == "table"


# ---------------------------------------------------------------------------
# Test: TXT Parser
# ---------------------------------------------------------------------------

class TestTXTParser:
    def test_parse_txt(self, sample_txt):
        doc = parse_document(str(sample_txt))
        assert doc.file_type == "txt"
        assert "Heading 1" in doc.text

    def test_txt_headings_detected(self, sample_txt):
        doc = parse_document(str(sample_txt))
        all_headings = []
        for page in doc.pages:
            all_headings.extend(page.headings)
        assert "Heading 1" in all_headings

    def test_txt_fallback_extension(self):
        """An unknown extension should fall through to TXT parser (.*)."""
        f = tempfile.NamedTemporaryFile(suffix=".log", delete=False)
        f.write(b"[INFO] Test log entry")
        f.close()
        try:
            doc = parse_document(f.name)
            assert "Test log entry" in doc.text
        finally:
            os.unlink(f.name)


# ---------------------------------------------------------------------------
# Test: Exception hierarchy
# ---------------------------------------------------------------------------

class TestExceptions:
    def test_parser_error_is_base(self):
        assert issubclass(UnsupportedFormatError, ParserError)
        assert issubclass(FileValidationError, ParserError)

    def test_unsupported_format_message(self):
        exc = UnsupportedFormatError(".xyz")
        assert ".xyz" in str(exc)

    def test_file_validation_message(self):
        exc = FileValidationError("PDF", "PK\x03\x04...")
        assert "PDF" in str(exc)


# ---------------------------------------------------------------------------
# Test: Excel Parser
# ---------------------------------------------------------------------------

class TestExcelParser:
    @pytest.fixture
    def sample_xlsx(self) -> Path:
        """Create a minimal .xlsx using openpyxl."""
        import openpyxl
        p = Path(tempfile.mktemp(suffix=".xlsx"))
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sheet1"
        ws.append(["Name", "Value"])
        ws.append(["Alpha", 10])
        ws.append(["Beta", 20])
        wb.save(str(p))
        wb.close()
        # Force garbage collection to release any lingering handles on Windows
        import gc
        gc.collect()
        yield p
        p.unlink(missing_ok=True)

    def test_parse_xlsx(self, sample_xlsx):
        doc = parse_document(str(sample_xlsx))
        assert doc.file_type == "xlsx"
        assert "Sheet1" in doc.text
        assert "Alpha" in doc.text

    def test_xlsx_page_count(self, sample_xlsx):
        doc = parse_document(str(sample_xlsx))
        assert len(doc.pages) >= 1

    def test_xlsx_blocks_are_tables(self, sample_xlsx):
        doc = parse_document(str(sample_xlsx))
        for page in doc.pages:
            for block in page.blocks:
                assert block.get("type") == "table"

    def test_xlsx_fails_on_non_ole(self):
        """Non-Excel content should fail magic-byte check."""
        f = tempfile.NamedTemporaryFile(suffix=".xlsx", mode="wb", delete=False)
        f.write(b"not an excel file")
        f.close()
        try:
            with pytest.raises(FileValidationError):
                parse_document(f.name)
        finally:
            os.unlink(f.name)


# ---------------------------------------------------------------------------
# Test: Image Parser
# ---------------------------------------------------------------------------

class TestImageParser:
    @pytest.fixture
    def sample_png(self) -> Path:
        """Create a minimal valid 1×1 PNG."""
        # Minimal 1x1 red PNG (IHDR + IDAT + IEND chunks)
        import struct, zlib
        def _make_png():
            sig = b'\x89PNG\r\n\x1a\n'
            ihdr_data = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)  # 1x1, 8-bit RGB
            ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff
            ihdr = struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc)
            # IDAT: single red pixel
            raw_data = b'\x00\xff\x00\x00'  # filter-byte 0, R=255, G=0, B=0
            compressed = zlib.compress(raw_data)
            idat_crc = zlib.crc32(b'IDAT' + compressed) & 0xffffffff
            idat = struct.pack('>I', len(compressed)) + b'IDAT' + compressed + struct.pack('>I', idat_crc)
            iend_crc = zlib.crc32(b'IEND') & 0xffffffff
            iend = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc)
            return sig + ihdr + idat + iend
        p = Path(tempfile.mktemp(suffix=".png"))
        p.write_bytes(_make_png())
        yield p
        p.unlink(missing_ok=True)

    def test_parse_png_returns_document_data(self, sample_png):
        doc = parse_document(str(sample_png))
        assert isinstance(doc, DocumentData)
        assert doc.file_type == "image"

    def test_image_metadata(self, sample_png):
        doc = parse_document(str(sample_png))
        assert "parser" in doc.metadata
        assert doc.metadata["parser"] == "Tesseract OCR"

    def test_image_is_ocr_flag(self, sample_png):
        doc = parse_document(str(sample_png))
        for page in doc.pages:
            assert page.is_ocr is True

    def test_image_fails_on_bogus_header(self):
        """File with .png extension but no PNG signature fails."""
        f = tempfile.NamedTemporaryFile(suffix=".png", mode="wb", delete=False)
        f.write(b"not a png")
        f.close()
        try:
            with pytest.raises(FileValidationError):
                parse_document(f.name)
        finally:
            os.unlink(f.name)


# ---------------------------------------------------------------------------
# Test: parse_document integration
# ---------------------------------------------------------------------------

class TestParseDocumentIntegration:
    def test_route_to_pdf(self, sample_pdf):
        doc = parse_document(str(sample_pdf))
        assert doc.file_type == "pdf"

    def test_route_to_txt(self, sample_txt):
        doc = parse_document(str(sample_txt))
        assert doc.file_type == "txt"

    def test_route_to_csv(self, sample_csv):
        doc = parse_document(str(sample_csv))
        assert doc.file_type == "csv"

    def test_unknown_extension_uses_fallback(self):
        """.log files should use the TXT parser's .* fallback."""
        f = tempfile.NamedTemporaryFile(suffix=".log", delete=False)
        f.write(b"test log line")
        f.close()
        try:
            doc = parse_document(f.name)
            assert doc is not None
        finally:
            os.unlink(f.name)

    def test_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            parse_document("/nonexistent/file.pdf")
