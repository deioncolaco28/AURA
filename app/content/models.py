"""
app/content/models.py

Data models for content intelligence in AURA.
Represents documents, sections, blocks, search results, summaries, and grounded Q&A.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ContentType(str, Enum):
    """Supported content and document types."""

    PDF = "PDF"
    DOCX = "DOCX"
    XLSX = "XLSX"
    PPTX = "PPTX"
    WEB = "WEB"
    TEXT = "TEXT"
    UNKNOWN = "UNKNOWN"


class BlockType(str, Enum):
    """Types of content blocks within a section."""

    HEADING = "HEADING"
    PARAGRAPH = "PARAGRAPH"
    TABLE = "TABLE"
    LIST_ITEM = "LIST_ITEM"
    CELL_RANGE = "CELL_RANGE"
    CODE = "CODE"
    RAW = "RAW"


@dataclass
class ContentBlock:
    """An atomic block of content (paragraph, table row, cell, heading)."""

    block_type: BlockType = BlockType.PARAGRAPH
    text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentSection:
    """A logical or structural section of a document (page, slide, sheet, section)."""

    title: str = ""
    location: str = ""  # e.g. "Page 1", "Slide 3", "Sheet1!A1:D10", "Section: Introduction"
    blocks: list[ContentBlock] = field(default_factory=list)
    raw_text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        """Return combined text of all blocks or raw_text."""
        if self.raw_text:
            return self.raw_text
        return "\n".join(b.text for b in self.blocks if b.text).strip()


@dataclass
class ContentDocument:
    """Unified representation of an extracted document across any supported format."""

    title: str = ""
    source_type: ContentType = ContentType.UNKNOWN
    source_path: str = ""
    sections: list[ContentSection] = field(default_factory=list)
    total_pages: int = 0
    slide_count: int = 0
    sheet_names: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        """Return full text across all sections."""
        return "\n\n".join(s.text for s in self.sections if s.text).strip()

    @property
    def section_count(self) -> int:
        return len(self.sections)

    @property
    def word_count(self) -> int:
        return len(self.full_text.split())


@dataclass
class ContentSearchResult:
    """A search match located within a document with provenance."""

    query: str
    document_path: str
    location: str  # e.g. "Page 4", "Slide 2", "Sheet1!B5"
    matched_text: str
    context: str = ""
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentSummary:
    """Structured summary of a document or section."""

    summary_text: str
    key_points: list[str] = field(default_factory=list)
    source_path: str = ""
    word_count: int = 0
    sections_covered: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentQAResult:
    """Grounded question answering result with provenance citations."""

    question: str
    answer: str
    source_path: str = ""
    provenance_location: str = ""  # e.g. "Page 3", "Slide 5", "Sheet1!C12"
    confidence: float = 1.0
    grounded_snippets: list[str] = field(default_factory=list)
    is_grounded: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
