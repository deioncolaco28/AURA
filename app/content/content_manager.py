"""
app/content/content_manager.py

Unified content intelligence manager for AURA.
Coordinates format detection, adapter delegation, task-scoped caching, summarization,
grounded Q&A, and document creation across PDF, DOCX, XLSX, PPTX, and Web content.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.content.adapters.base import BaseContentAdapter
from app.content.adapters.docx_adapter import DOCXAdapter
from app.content.adapters.pdf_adapter import PDFAdapter
from app.content.adapters.pptx_adapter import PPTXAdapter
from app.content.adapters.web_adapter import WebContentAdapter
from app.content.adapters.xlsx_adapter import XLSXAdapter
from app.content.models import (
    ContentDocument,
    ContentQAResult,
    ContentSearchResult,
    ContentSummary,
    ContentType,
)
from app.content.qa_engine import ContentQAEngine
from app.content.summarizer import ContentSummarizer


class ContentManager:
    """
    Central manager for extracting, searching, analyzing, and generating document content.
    """

    def __init__(
        self,
        pdf_adapter: PDFAdapter | None = None,
        docx_adapter: DOCXAdapter | None = None,
        xlsx_adapter: XLSXAdapter | None = None,
        pptx_adapter: PPTXAdapter | None = None,
        web_adapter: WebContentAdapter | None = None,
        summarizer: ContentSummarizer | None = None,
        qa_engine: ContentQAEngine | None = None,
    ):
        self.pdf_adapter = pdf_adapter or PDFAdapter()
        self.docx_adapter = docx_adapter or DOCXAdapter()
        self.xlsx_adapter = xlsx_adapter or XLSXAdapter()
        self.pptx_adapter = pptx_adapter or PPTXAdapter()
        self.web_adapter = web_adapter or WebContentAdapter()
        self.summarizer = summarizer or ContentSummarizer()
        self.qa_engine = qa_engine or ContentQAEngine()

        # Task-scoped document extraction cache: {path_or_url: ContentDocument}
        self._doc_cache: dict[str, ContentDocument] = {}

    def detect_type(self, source: str) -> ContentType:
        """Infer ContentType from URL or file extension."""
        s = source.strip().lower()
        if s.startswith("http://") or s.startswith("https://") or s.endswith(".html") or s.endswith(".htm"):
            return ContentType.WEB
        if s.endswith(".pdf"):
            return ContentType.PDF
        if s.endswith(".docx"):
            return ContentType.DOCX
        if s.endswith(".xlsx") or s.endswith(".xls") or s.endswith(".csv"):
            return ContentType.XLSX
        if s.endswith(".pptx") or s.endswith(".ppt"):
            return ContentType.PPTX
        if s.endswith(".txt") or s.endswith(".md"):
            return ContentType.TEXT
        return ContentType.UNKNOWN

    def get_adapter(self, content_type: ContentType) -> BaseContentAdapter:
        """Retrieve appropriate adapter for the content type."""
        if content_type == ContentType.PDF:
            return self.pdf_adapter
        if content_type == ContentType.DOCX:
            return self.docx_adapter
        if content_type == ContentType.XLSX:
            return self.xlsx_adapter
        if content_type == ContentType.PPTX:
            return self.pptx_adapter
        if content_type == ContentType.WEB:
            return self.web_adapter
        # Default fallback to DOCX/Web text adapter
        return self.docx_adapter

    def extract(self, source_path_or_url: str, force_reload: bool = False) -> ContentDocument:
        """Extract and index content from a source file or URL with task-scoped caching."""
        cache_key = str(source_path_or_url).strip()
        if not force_reload and cache_key in self._doc_cache:
            return self._doc_cache[cache_key]

        ctype = self.detect_type(source_path_or_url)
        adapter = self.get_adapter(ctype)

        doc = adapter.extract(source_path_or_url)
        self._doc_cache[cache_key] = doc
        return doc

    def search(self, source_path_or_url: str, query: str) -> list[ContentSearchResult]:
        """Search inside a document or web page with exact provenance."""
        doc = self.extract(source_path_or_url)
        ctype = self.detect_type(source_path_or_url)
        adapter = self.get_adapter(ctype)
        return adapter.search(doc, query)

    def summarize(
        self,
        source_path_or_url: str,
        max_points: int = 5,
        section_filter: str | None = None,
    ) -> ContentSummary:
        """Extract and summarize a document or web page."""
        doc = self.extract(source_path_or_url)
        return self.summarizer.summarize(doc, max_points=max_points, section_filter=section_filter)

    def answer_question(self, source_path_or_url: str, question: str) -> ContentQAResult:
        """Answer a question grounded in the extracted document content."""
        doc = self.extract(source_path_or_url)
        return self.qa_engine.answer_question(doc, question)

    def create_document(
        self,
        format_type: str | ContentType,
        output_path: str,
        title: str = "Document",
        content: Any = None,
        key_points: list[str] | None = None,
        slides: list[dict[str, Any]] | None = None,
        headers: list[str] | None = None,
        rows: list[list[Any]] | None = None,
    ) -> str:
        """Create a new formatted DOCX, XLSX, or PPTX file."""
        fmt = str(format_type).upper()
        if "DOCX" in fmt or output_path.endswith(".docx"):
            return self.docx_adapter.create_document(
                output_path=output_path,
                title=title,
                content=content or "",
                key_points=key_points,
            )
        elif "PPTX" in fmt or output_path.endswith(".pptx"):
            return self.pptx_adapter.create_presentation(
                output_path=output_path,
                title=title,
                slides=slides or ([{"title": title, "bullets": key_points}] if key_points else []),
            )
        elif "XLSX" in fmt or output_path.endswith(".xlsx"):
            return self.xlsx_adapter.create_spreadsheet(
                output_path=output_path,
                headers=headers or [],
                rows=rows or [],
            )
        else:
            # Fallback default DOCX
            return self.docx_adapter.create_document(
                output_path=output_path,
                title=title,
                content=content or "",
            )

    def analyze_spreadsheet(
        self,
        source_path: str,
        sheet_name: str | None = None,
        column: str | int | None = None,
    ) -> dict[str, Any]:
        """Compute statistics and structure for an Excel workbook."""
        return self.xlsx_adapter.analyze_sheet(
            source_path=source_path,
            sheet_name=sheet_name,
            column=column,
        )

    def clear_cache(self) -> None:
        """Clear task-scoped extraction cache."""
        self._doc_cache.clear()
