"""
tests/test_trace_and_metrics.py

Unit tests for structured task traces, execution metrics, and performance timing.
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from app.core.performance import PerformanceTimer, measure_time
from app.logging.logger import AURALogger
from app.logging.trace import ExecutionMetrics, TaskTrace, TaskTraceEvent


class TestTraceAndMetrics:
    def test_execution_metrics_serialization(self):
        metrics = ExecutionMetrics(
            total_duration_ms=1200.5,
            planning_duration_ms=150.0,
            action_duration_ms=800.0,
            verification_duration_ms=250.5,
            attempts_count=2,
            replans_count=1,
        )
        d = metrics.to_dict()
        assert d["total_duration_ms"] == 1200.5
        assert d["attempts_count"] == 2
        assert d["replans_count"] == 1

    def test_task_trace_event_creation(self):
        event = TaskTraceEvent(
            task_id="task_001",
            node_id="node_1",
            goal="Open Notepad",
            action="LAUNCH_APP",
            target="notepad.exe",
            duration_ms=350.0,
            status="COMPLETED",
            verification_result={"success": True},
        )
        d = event.to_dict()
        assert d["task_id"] == "task_001"
        assert d["action"] == "LAUNCH_APP"
        assert d["status"] == "COMPLETED"

    def test_task_trace_lifecycle_and_jsonl_export(self):
        with TemporaryDirectory() as tmp_dir:
            trace_file = Path(tmp_dir) / "test_traces.jsonl"

            trace = TaskTrace(task_id="task_test_123", goal="Open Calculator")
            trace.add_event(
                TaskTraceEvent(
                    task_id=trace.task_id,
                    action="LAUNCH_APP",
                    target="calc.exe",
                    duration_ms=400.0,
                    status="COMPLETED",
                )
            )
            trace.complete(status="COMPLETED")

            trace.save_jsonl(trace_file)
            assert trace_file.exists()

            with trace_file.open("r", encoding="utf-8") as f:
                lines = f.readlines()
                assert len(lines) == 1
                loaded = json.loads(lines[0])
                assert loaded["task_id"] == "task_test_123"
                assert loaded["status"] == "COMPLETED"
                assert len(loaded["events"]) == 1

    def test_logger_record_trace(self):
        with TemporaryDirectory() as tmp_dir:
            logger = AURALogger(log_directory=tmp_dir)
            trace = TaskTrace(task_id="task_logged_456", goal="Create Folder")
            trace.complete()

            logger.record_trace(trace)
            assert logger.trace_file.exists()

    def test_performance_timer(self):
        timer = PerformanceTimer()
        timer.start()
        # busy wait a tiny fraction
        for _ in range(1000):
            pass
        elapsed = timer.stop()
        assert elapsed > 0.0
        assert timer.elapsed_ms == elapsed

    def test_measure_time_context_manager(self):
        with measure_time() as timing:
            for _ in range(1000):
                pass
        assert "elapsed_ms" in timing
        assert timing["elapsed_ms"] >= 0.0
