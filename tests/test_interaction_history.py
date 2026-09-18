"""Tests for InteractionHistory."""

import pytest
import time

from app.intelligence.interaction_history import (
    InteractionHistory,
    InteractionRecord,
)


class TestInteractionHistory:

    def test_empty_history_neutral_success_rate(self):
        history = InteractionHistory()
        rate = history.success_rate("Notepad")
        assert rate == 0.5  # neutral prior

    def test_record_success(self):
        history = InteractionHistory()
        rec = history.record(
            task="open notepad",
            target="Notepad",
            element_id="1",
            element_text="Notepad",
            score=0.95,
            verification_result="success",
        )
        assert isinstance(rec, InteractionRecord)
        assert rec.succeeded

    def test_record_failure(self):
        history = InteractionHistory()
        rec = history.record(
            target="Notepad",
            element_text="Notepad",
            verification_result="failure",
        )
        assert rec.failed

    def test_success_rate_all_success(self):
        history = InteractionHistory()
        for _ in range(3):
            history.record(
                target="Notepad",
                element_text="Notepad",
                verification_result="success",
            )
        assert history.success_rate("Notepad") == 1.0

    def test_success_rate_all_failure(self):
        history = InteractionHistory()
        for _ in range(2):
            history.record(
                target="Notepad",
                element_text="Notepad",
                verification_result="failure",
            )
        assert history.success_rate("Notepad") == 0.0

    def test_success_rate_mixed(self):
        history = InteractionHistory()
        history.record(target="Btn", element_text="Btn", verification_result="success")
        history.record(target="Btn", element_text="Btn", verification_result="success")
        history.record(target="Btn", element_text="Btn", verification_result="failure")
        rate = history.success_rate("Btn")
        assert rate == pytest.approx(2 / 3)

    def test_success_rate_unknown_excluded(self):
        """Records with verification_result='unknown' should not count."""
        history = InteractionHistory()
        history.record(target="X", element_text="X", verification_result="unknown")
        assert history.success_rate("X") == 0.5  # still neutral prior

    def test_success_rate_case_insensitive(self):
        history = InteractionHistory()
        history.record(
            target="notepad",
            element_text="notepad",
            verification_result="success",
        )
        assert history.success_rate("Notepad") == 1.0

    def test_all_records_returns_all(self):
        history = InteractionHistory()
        history.record(target="A", element_text="A", verification_result="success")
        history.record(target="B", element_text="B", verification_result="failure")
        records = history.all_records()
        assert len(records) == 2

    def test_recent_records_limit(self):
        history = InteractionHistory()
        for i in range(30):
            history.record(target=f"Item{i}", element_text=f"Item{i}")
        recent = history.recent_records(limit=10)
        assert len(recent) == 10

    def test_clear(self):
        history = InteractionHistory()
        history.record(target="A", element_text="A", verification_result="success")
        history.clear()
        assert history.all_records() == []
        assert history.success_rate("A") == 0.5

    def test_record_has_timestamp(self):
        history = InteractionHistory()
        before = time.time()
        rec = history.record(target="A")
        after = time.time()
        assert before <= rec.timestamp <= after

    def test_persistence(self, tmp_path):
        """Records should survive save/load cycle."""
        path = tmp_path / "history.json"

        h1 = InteractionHistory(persistence_path=path)
        h1.record(
            target="Notepad",
            element_text="Notepad",
            verification_result="success",
        )

        # Load from same path.
        h2 = InteractionHistory(persistence_path=path)
        assert len(h2.all_records()) == 1
        assert h2.success_rate("Notepad") == 1.0
