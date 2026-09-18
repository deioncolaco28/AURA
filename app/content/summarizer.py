"""
app/content/summarizer.py

Deterministic summarization engine for documents and web content in AURA.
Extracts key themes, sentences, and structured bullet highlights with section coverage.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from app.content.models import ContentDocument, ContentSection, ContentSummary


class ContentSummarizer:
    """
    Summarizes ContentDocument or raw text using extractive sentence ranking
    and key highlight generation.
    """

    STOPWORDS = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with",
        "by", "about", "as", "into", "like", "through", "after", "over", "between",
        "out", "against", "during", "without", "before", "under", "around", "among",
        "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do",
        "does", "did", "this", "that", "these", "those", "it", "its", "of", "from",
    }

    def summarize(
        self,
        document_or_text: ContentDocument | str,
        max_points: int = 5,
        section_filter: str | None = None,
    ) -> ContentSummary:
        """Produce a structured ContentSummary."""
        if isinstance(document_or_text, ContentDocument):
            doc = document_or_text
            source_path = doc.source_path
            sections = doc.sections
            if section_filter:
                sections = [
                    s for s in sections
                    if section_filter.lower() in s.title.lower() or section_filter.lower() in s.location.lower()
                ] or sections
            full_text = "\n\n".join(s.text for s in sections if s.text).strip()
            sections_covered = [s.location or s.title for s in sections if s.text]
        else:
            full_text = str(document_or_text).strip()
            source_path = "raw_text"
            sections_covered = ["Full Text"]

        if not full_text:
            return ContentSummary(
                summary_text="No content available to summarize.",
                key_points=[],
                source_path=source_path,
                word_count=0,
                sections_covered=[],
            )

        # Split sentences
        sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+", full_text)
            if len(s.strip().split()) >= 4
        ]

        if not sentences:
            sentences = [full_text]

        # Calculate word frequencies (excluding stopwords)
        words = re.findall(r"\b[a-zA-Z]{3,}\b", full_text.lower())
        word_freq = Counter(w for w in words if w not in self.STOPWORDS)

        # Score sentences
        scored_sentences: list[tuple[float, int, str]] = []
        for idx, sentence in enumerate(sentences):
            s_words = re.findall(r"\b[a-zA-Z]{3,}\b", sentence.lower())
            if not s_words:
                continue
            score = sum(word_freq.get(w, 0) for w in s_words) / len(s_words)
            # Boost early sentences in sections
            if idx < 3:
                score *= 1.2
            scored_sentences.append((score, idx, sentence))

        # Select top N sentences sorted by document order
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        top_sentences = sorted(scored_sentences[:max_points], key=lambda x: x[1])

        key_points = [s[2] for s in top_sentences]
        summary_text = " ".join(key_points)

        return ContentSummary(
            summary_text=summary_text,
            key_points=key_points,
            source_path=source_path,
            word_count=len(full_text.split()),
            sections_covered=sections_covered[:10],
            metadata={"extracted_sentence_count": len(key_points)},
        )
