"""
Tests for PPTXAdapter: slides, titles, notes, search, and slide deck creation.
"""

from __future__ import annotations

from pathlib import Path
import pptx
import pytest

from app.content.adapters.pptx_adapter import PPTXAdapter
from app.content.models import ContentType


def _create_sample_pptx(path: Path) -> None:
    prs = pptx.Presentation()
    slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(slide_layout)
    slide.shapes.title.text = "AURA Architecture"
    slide.placeholders[1].text = "Computer Use Assistant"
    
    # Slide 2 with bullet points
    slide2 = prs.slides.add_slide(prs.slide_layouts[1])
    slide2.shapes.title.text = "Key Components"
    tf = slide2.placeholders[1].text_frame
    tf.text = "TaskGraph Engine"
    p = tf.add_paragraph()
    p.text = "Perception Fusion"
    
    prs.save(str(path))


class TestPPTXAdapter:
    def test_extract_pptx_slides_and_titles(self, tmp_path):
        pptx_path = tmp_path / "deck.pptx"
        _create_sample_pptx(pptx_path)

        adapter = PPTXAdapter()
        doc = adapter.extract(str(pptx_path))

        assert doc.source_type == ContentType.PPTX
        assert doc.slide_count == 2
        assert len(doc.sections) == 2
        assert "AURA Architecture" in doc.sections[0].title
        assert "TaskGraph Engine" in doc.full_text

    def test_search_pptx_with_slide_provenance(self, tmp_path):
        pptx_path = tmp_path / "deck.pptx"
        _create_sample_pptx(pptx_path)

        adapter = PPTXAdapter()
        doc = adapter.extract(str(pptx_path))

        results = adapter.search(doc, "Perception")
        assert len(results) == 1
        assert "Slide 2" in results[0].location
        assert "Perception Fusion" in results[0].context

    def test_create_presentation(self, tmp_path):
        out_path = tmp_path / "created.pptx"
        adapter = PPTXAdapter()

        created = adapter.create_presentation(
            output_path=out_path,
            title="Generated Pitch",
            subtitle="Automated Report",
            slides=[
                {"title": "Overview", "bullets": ["First point", "Second point"]},
            ],
        )

        assert Path(created).exists()
        doc = adapter.extract(created)
        assert doc.slide_count == 2
        assert "First point" in doc.full_text
