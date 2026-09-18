"""
Tests for WebContentAdapter: HTML extraction, article parsing, and DOM section search.
"""

from __future__ import annotations

import pytest

from app.content.adapters.web_adapter import WebContentAdapter
from app.content.models import ContentType


class TestWebContentAdapter:
    def test_extract_html_content(self):
        html = """
        <html>
            <head><title>AURA Web Documentation</title></head>
            <body>
                <header><nav>Home | Docs</nav></header>
                <h1>Introduction</h1>
                <p>AURA is an autonomous computer-use agent for Windows.</p>
                <h2>Methodology</h2>
                <p>The system uses deterministic task graphs and multi-modal perception.</p>
                <footer>Copyright 2026</footer>
            </body>
        </html>
        """

        adapter = WebContentAdapter()
        doc = adapter.extract("https://example.com/docs", html_content=html)

        assert doc.source_type == ContentType.WEB
        assert doc.title == "AURA Web Documentation"
        assert len(doc.sections) >= 2
        # Ensure boilerplate is stripped
        assert "Copyright" not in doc.full_text
        assert "Home | Docs" not in doc.full_text
        assert "AURA is an autonomous computer-use agent" in doc.full_text

    def test_search_web_with_dom_provenance(self):
        html = """
        <html><body>
            <h1>Pricing</h1>
            <p>Community edition is free and open-source.</p>
        </body></html>
        """
        adapter = WebContentAdapter()
        doc = adapter.extract("https://example.com/pricing", html_content=html)

        results = adapter.search(doc, "Community")
        assert len(results) == 1
        assert "DOM:" in results[0].location
        assert "free and open-source" in results[0].context
