"""
Tests for PDFAdapter: text extraction, page indexing, and search with provenance.
"""

from __future__ import annotations

from pathlib import Path
import pytest
import pypdf

from app.content.adapters.pdf_adapter import PDFAdapter
from app.content.models import ContentType


def _create_sample_pdf(path: Path) -> None:
    writer = pypdf.PdfWriter()
    
    # Page 1
    writer.add_blank_page(width=300, height=300)
    # Page 2
    writer.add_blank_page(width=300, height=300)
    
    with open(path, "wb") as f:
        writer.write(f)


class TestPDFAdapter:
    def test_extract_pdf_pages_and_metadata(self, tmp_path):
        pdf_path = tmp_path / "sample.pdf"
        _create_sample_pdf(pdf_path)

        adapter = PDFAdapter()
        doc = adapter.extract(str(pdf_path))

        assert doc.source_type == ContentType.PDF
        assert doc.total_pages == 2
        assert len(doc.sections) == 2
        assert doc.sections[0].location == "Page 1"
        assert doc.sections[1].location == "Page 2"

    def test_extract_nonexistent_pdf_raises_error(self, tmp_path):
        adapter = PDFAdapter()
        with pytest.raises(FileNotFoundError):
            adapter.extract(str(tmp_path / "nonexistent.pdf"))

    def test_search_pdf_with_provenance(self, tmp_path):
        pdf_path = tmp_path / "sample.pdf"
        _create_sample_pdf(pdf_path)

        adapter = PDFAdapter()
        doc = adapter.extract(str(pdf_path))
        # Mock text in page 1
        doc.sections[0].raw_text = "The experimental methodology involves multi-modal agent reasoning."

        results = adapter.search(doc, "methodology")
        assert len(results) == 1
        assert results[0].location == "Page 1"
        assert "methodology" in results[0].matched_text.lower()
