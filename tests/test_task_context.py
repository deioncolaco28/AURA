"""
Tests for TaskContext and EntityResolver.
"""

from __future__ import annotations

import pytest

from app.intelligence.task_context import EntityResolver, TaskContext


class TestTaskContext:
    def test_entity_storage_and_resolution(self):
        ctx = TaskContext(goal="Find and move report")
        ctx.set_entity("report", "C:/Users/test/Downloads/report.docx")
        ctx.set_entity("$folder", "C:/Users/test/Downloads/AURA")

        assert ctx.get_entity("report") == "C:/Users/test/Downloads/report.docx"
        assert ctx.get_entity("folder") == "C:/Users/test/Downloads/AURA"

        resolver = EntityResolver(ctx)
        resolved_str = resolver.resolve("move $report to $folder")
        assert resolved_str == "move C:/Users/test/Downloads/report.docx to C:/Users/test/Downloads/AURA"

    def test_pronoun_reference_resolution(self):
        ctx = TaskContext()
        ctx.set_entity("report", "C:/data/summary.pdf")

        resolver = EntityResolver(ctx)
        assert resolver.resolve("it") == "C:/data/summary.pdf"
        assert resolver.resolve("that") == "C:/data/summary.pdf"
        assert resolver.resolve("this file") == "C:/data/summary.pdf"

    def test_intermediate_results(self):
        ctx = TaskContext()
        ctx.store_result("step_extract", "extracted_text", "AI Agent Summary")
        assert ctx.get_result("step_extract", "extracted_text") == "AI Agent Summary"
        assert ctx.get_result("step_extract", "non_existent") is None

    def test_context_clear(self):
        ctx = TaskContext(goal="Sample Goal")
        ctx.set_entity("item", "123")
        ctx.completed_tasks.append("step_1")

        ctx.clear()
        assert ctx.goal == ""
        assert len(ctx.entities) == 0
        assert len(ctx.completed_tasks) == 0
