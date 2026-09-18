"""
app/content/adapters/base.py

Base adapter interface for document and web content extractors in AURA.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.content.models import ContentDocument, ContentSearchResult


class BaseContentAdapter(ABC):
    """Abstract base adapter for file and web content extraction."""

    @abstractmethod
    def extract(self, source_path_or_url: str) -> ContentDocument:
        """Extract content from source into a structured ContentDocument."""
        pass

    def search(self, document: ContentDocument, query: str) -> list[ContentSearchResult]:
        """Search for occurrences of query in the extracted document."""
        results: list[ContentSearchResult] = []
        q_clean = query.strip().lower()

        for section in document.sections:
            text = section.text
            if q_clean in text.lower():
                # Extract surrounding context
                idx = text.lower().find(q_clean)
                start = max(0, idx - 60)
                end = min(len(text), idx + len(q_clean) + 60)
                context = text[start:end].replace("\n", " ").strip()

                results.append(
                    ContentSearchResult(
                        query=query,
                        document_path=document.source_path,
                        location=section.location or section.title or "Document",
                        matched_text=text[idx : idx + len(q_clean)],
                        context=f"...{context}...",
                        confidence=1.0,
                    )
                )

        return results
