"""
app/content/qa_engine.py

Grounded Question Answering engine over documents and web content in AURA.
Retrieves relevant sections and synthesizes answers with provenance citations.
"""

from __future__ import annotations

import re
from typing import Any

from app.content.models import ContentDocument, ContentQAResult, ContentSection


class ContentQAEngine:
    """
    Answers questions grounded in ContentDocument sections without hallucination.
    """

    STOPWORDS = {
        "what", "which", "where", "when", "who", "how", "why", "is", "are", "was", "were",
        "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "with", "about",
        "does", "do", "did", "tell", "me", "say", "report", "document", "this", "that",
    }

    def answer_question(
        self,
        document: ContentDocument,
        question: str,
    ) -> ContentQAResult:
        """Find relevant content in document and synthesize a grounded answer."""
        q_words = [
            w for w in re.findall(r"\b[a-zA-Z0-9_]{3,}\b", question.lower())
            if w not in self.STOPWORDS
        ]

        if not q_words or not document.sections:
            return ContentQAResult(
                question=question,
                answer="I couldn't find enough information in the document to answer that reliably.",
                source_path=document.source_path,
                provenance_location="",
                confidence=0.0,
                is_grounded=False,
            )

        scored_sections: list[tuple[float, ContentSection, list[str]]] = []

        for section in document.sections:
            text = section.text
            if not text:
                continue

            matches = []
            score = 0.0

            for w in q_words:
                count = len(re.findall(r"\b" + re.escape(w) + r"\b", text.lower()))
                if count > 0:
                    score += count * 2.0
                    matches.append(w)
                elif w in text.lower():
                    score += 1.0
                    matches.append(w)

            if score > 0:
                # Find sentences with matching keywords
                sentences = re.split(r"(?<=[.!?])\s+", text)
                matched_sentences = [
                    s.strip() for s in sentences
                    if any(w in s.lower() for w in q_words)
                ]
                scored_sections.append((score, section, matched_sentences or [text[:200]]))

        if not scored_sections:
            return ContentQAResult(
                question=question,
                answer="I couldn't find enough information in the document to answer that reliably.",
                source_path=document.source_path,
                provenance_location="",
                confidence=0.0,
                is_grounded=False,
            )

        # Sort by relevance score
        scored_sections.sort(key=lambda x: x[0], reverse=True)
        best_score, best_section, best_snippets = scored_sections[0]

        loc = best_section.location or best_section.title or "Document"
        answer_text = " ".join(best_snippets[:3])

        return ContentQAResult(
            question=question,
            answer=f"{answer_text}\n\nSource: {loc}.",
            source_path=document.source_path,
            provenance_location=loc,
            confidence=min(1.0, best_score / (len(q_words) * 2.0)),
            grounded_snippets=best_snippets[:3],
            is_grounded=True,
            metadata={"matched_section": best_section.title, "score": best_score},
        )
