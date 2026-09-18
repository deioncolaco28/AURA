"""
app/automation/environments/content_environment.py

Execution environment representing Content Intelligence tools and adapters in AURA.
"""

from __future__ import annotations

from typing import Any

from app.automation.environments.environment import (
    Environment,
    EnvironmentCapability,
)
from app.content.content_manager import ContentManager


class ContentEnvironment(Environment):
    """
    Environment dedicated to document understanding, search, summarization,
    Q&A, and document creation.
    """

    def __init__(self, content_manager: ContentManager | None = None):
        self.content_manager = content_manager or ContentManager()

    @property
    def name(self) -> str:
        return "content"

    def supported_capabilities(self) -> set[EnvironmentCapability]:
        return {
            EnvironmentCapability.CONTENT_EXTRACT,
            EnvironmentCapability.CONTENT_SEARCH,
            EnvironmentCapability.CONTENT_SUMMARIZE,
            EnvironmentCapability.CONTENT_QA,
            EnvironmentCapability.CONTENT_CREATE_DOCX,
            EnvironmentCapability.CONTENT_CREATE_XLSX,
            EnvironmentCapability.CONTENT_CREATE_PPTX,
            EnvironmentCapability.CONTENT_ANALYZE_SHEET,
        }

    def extract(self, source_path_or_url: str) -> Any:
        return self.content_manager.extract(source_path_or_url)

    def search(self, source_path_or_url: str, query: str) -> Any:
        return self.content_manager.search(source_path_or_url, query)

    def summarize(self, source_path_or_url: str, max_points: int = 5) -> Any:
        return self.content_manager.summarize(source_path_or_url, max_points=max_points)

    def answer_question(self, source_path_or_url: str, question: str) -> Any:
        return self.content_manager.answer_question(source_path_or_url, question)

    def create_document(self, format_type: str, output_path: str, **kwargs) -> str:
        return self.content_manager.create_document(format_type, output_path, **kwargs)

    def analyze_spreadsheet(self, source_path: str, **kwargs) -> Any:
        return self.content_manager.analyze_spreadsheet(source_path, **kwargs)
