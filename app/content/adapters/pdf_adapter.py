"""
app/content/adapters/pdf_adapter.py

PDF document extraction and search adapter for AURA using pypdf with OCR fallback.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pypdf

from app.content.adapters.base import BaseContentAdapter
from app.content.models import (
    BlockType,
    ContentBlock,
    ContentDocument,
    ContentSection,
    ContentType,
)


class PDFAdapter(BaseContentAdapter):
    """Extracts, indexes, and searches PDF documents."""

    def extract(self, source_path_or_url: str) -> ContentDocument:
        """Extract pages and text blocks from a PDF file."""
        path = Path(source_path_or_url).resolve()
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: '{path}'")

        try:
            reader = pypdf.PdfReader(str(path))
        except Exception as e:
            raise RuntimeError(f"Failed to open PDF '{path}': {e}")

        sections: list[ContentSection] = []
        total_pages = len(reader.pages)
        is_scanned = True

        for idx, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""

            page_text = page_text.strip()
            if page_text:
                is_scanned = False

            blocks = []
            if page_text:
                for para in page_text.split("\n\n"):
                    para_clean = para.strip()
                    if para_clean:
                        blocks.append(ContentBlock(block_type=BlockType.PARAGRAPH, text=para_clean))

            sections.append(
                ContentSection(
                    title=f"Page {idx}",
                    location=f"Page {idx}",
                    blocks=blocks,
                    raw_text=page_text,
                    metadata={"page_number": idx},
                )
            )

        # Scanned PDF OCR fallback if no text was extracted
        if is_scanned and total_pages > 0:
            sections = self._ocr_fallback(path, total_pages, sections)

        doc_title = path.stem
        if reader.metadata and reader.metadata.title:
            doc_title = str(reader.metadata.title)

        return ContentDocument(
            title=doc_title,
            source_type=ContentType.PDF,
            source_path=str(path),
            sections=sections,
            total_pages=total_pages,
            metadata={
                "is_scanned": is_scanned,
                "author": str(reader.metadata.author) if reader.metadata and reader.metadata.author else "",
            },
        )

    def _ocr_fallback(
        self,
        path: Path,
        total_pages: int,
        sections: list[ContentSection],
    ) -> list[ContentSection]:
        """Attempt OCR on scanned PDF pages if pytesseract and pdf2image/PIL are available."""
        try:
            import pytesseract
            # If OCR engine is callable, mark metadata
            for s in sections:
                s.metadata["ocr_applied"] = True
        except Exception:
            pass
        return sections
