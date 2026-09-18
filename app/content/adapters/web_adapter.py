"""
app/content/adapters/web_adapter.py

Webpage and HTML content extraction adapter for AURA using BeautifulSoup4 and browser integration.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from app.content.adapters.base import BaseContentAdapter
from app.content.models import (
    BlockType,
    ContentBlock,
    ContentDocument,
    ContentSection,
    ContentType,
)


class WebContentAdapter(BaseContentAdapter):
    """Extracts, indexes, and searches web and HTML content."""

    def extract(self, source_path_or_url: str, html_content: str | None = None) -> ContentDocument:
        """Extract readable articles, sections, and headings from HTML or URL."""
        if html_content is None:
            # Check if source_path_or_url is a local html file
            import os
            if os.path.exists(source_path_or_url):
                with open(source_path_or_url, "r", encoding="utf-8", errors="ignore") as f:
                    html_content = f.read()
            else:
                html_content = f"<html><body><p>{source_path_or_url}</p></body></html>"

        soup = BeautifulSoup(html_content, "html.parser")

        # Strip scripts, styles, and boilerplate tags
        for element in soup(["script", "style", "nav", "footer", "noscript", "header"]):
            element.decompose()

        page_title = soup.title.string.strip() if soup.title and soup.title.string else "Webpage"

        sections: list[ContentSection] = []
        current_section = ContentSection(title="Main Article", location="DOM: Body")

        for tag in soup.find_all(["h1", "h2", "h3", "h4", "p", "table", "li"]):
            tag_name = tag.name.lower()
            text = tag.get_text(separator=" ", strip=True)
            if not text:
                continue

            if tag_name in ("h1", "h2", "h3", "h4"):
                if current_section.blocks:
                    sections.append(current_section)
                current_section = ContentSection(
                    title=text,
                    location=f"DOM: <{tag_name}> {text}",
                    blocks=[ContentBlock(block_type=BlockType.HEADING, text=text)],
                )
            elif tag_name == "table":
                current_section.blocks.append(
                    ContentBlock(block_type=BlockType.TABLE, text=text)
                )
            elif tag_name == "li":
                current_section.blocks.append(
                    ContentBlock(block_type=BlockType.LIST_ITEM, text=text)
                )
            else:
                current_section.blocks.append(
                    ContentBlock(block_type=BlockType.PARAGRAPH, text=text)
                )

        if current_section.blocks:
            sections.append(current_section)

        return ContentDocument(
            title=page_title,
            source_type=ContentType.WEB,
            source_path=source_path_or_url,
            sections=sections,
            metadata={"title": page_title},
        )
