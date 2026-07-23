"""
Image Parser — Tesseract OCR

Extracts text from images (PNG, JPG, TIFF, BMP, WEBP) using
Tesseract OCR with word-level bounding boxes.
"""

from __future__ import annotations

import os

import pytesseract
from PIL import Image

from .base import BaseParser, DocumentData, PageData
from .exceptions import OCRError, ParsingInterruptedError


class ImageParser(BaseParser):
    """Parse raster image files with OCR."""

    def supported_extensions(self) -> list[str]:
        return [".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"]

    def parse(self, file_path: str) -> DocumentData:
        filename = os.path.basename(file_path)
        text = ""
        blocks: list[dict] = []

        try:
            img = Image.open(file_path)
        except Exception as exc:
            # Return a minimal DocumentData so the pipeline can
            # record a failed parse rather than crashing the upload.
            return DocumentData(
                filename=filename,
                file_type="image",
                text=f"Image open error: {exc}",
                metadata={"parser": "Tesseract OCR", "error": str(exc)},
                pages=[PageData(page_number=1, text=f"Error: {exc}", blocks=[])],
            )

        timeout = self.get_ocr_timeout()

        try:
            text = pytesseract.image_to_string(img, timeout=timeout)
            ocr_dict = pytesseract.image_to_data(
                img, output_type=pytesseract.Output.DICT, timeout=timeout
            )

            n_boxes = len(ocr_dict.get("level", []))
            for i in range(n_boxes):
                word = ocr_dict["text"][i].strip()
                if word:
                    blocks.append(
                        {
                            "text": word,
                            "bbox": (
                                ocr_dict["left"][i],
                                ocr_dict["top"][i],
                                ocr_dict["left"][i] + ocr_dict["width"][i],
                                ocr_dict["top"][i] + ocr_dict["height"][i],
                            ),
                            "type": "word",
                        }
                    )
        except Exception as exc:
            # Degrade gracefully — return what we have so the
            # pipeline can record a partial-failure document
            # instead of crashing the upload with a 500.
            print(f"    [Image Parser] OCR failed: {exc}", flush=True)
            text = ""

        page = PageData(
            page_number=1,
            text=text.strip(),
            blocks=blocks,
            headings=[filename],
            is_ocr=True,
        )

        return DocumentData(
            filename=filename,
            file_type="image",
            text=text.strip(),
            metadata={"parser": "Tesseract OCR", "blocks_count": len(blocks)},
            pages=[page],
        )
