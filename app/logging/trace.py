"""
app/logging/trace.py

Machine-readable structured task trace and execution metrics for AURA.
Enables fine-grained auditability, reproduction, and research evaluation.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ExecutionMetrics:
    """Quantitative performance and resource counters for a task execution."""
    total_duration_ms: float = 0.0
    planning_duration_ms: float = 0.0
    perception_duration_ms: float = 0.0
    action_duration_ms: float = 0.0
    verification_duration_ms: float = 0.0
    recovery_duration_ms: float = 0.0
    attempts_count: int = 0
    observations_count: int = 0
    replans_count: int = 0
    recovery_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskTraceEvent:
    """Individual execution step trace record."""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    task_id: str = ""
    node_id: str = ""
    goal: str = ""
    action: str = ""
    target: str = ""
    strategy: str = ""
    attempt: int = 1
    duration_ms: float = 0.0
    status: str = "COMPLETED"  # "COMPLETED" | "FAILED" | "SKIPPED" | "CANCELLED"
    expected_state: dict[str, Any] | None = None
    verification_result: dict[str, Any] | None = None
    failure_type: str | None = None
    recovery_strategy: str | None = None
    pre_observation_summary: dict[str, Any] | None = None
    post_observation_summary: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskTrace:
    """Complete execution record for a task or DAG run."""
    task_id: str
    goal: str
    mode: str = "DO_IT_FOR_ME"
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: str | None = None
    status: str = "RUNNING"  # "COMPLETED" | "FAILED" | "CANCELLED"
    events: list[TaskTraceEvent] = field(default_factory=list)
    metrics: ExecutionMetrics = field(default_factory=ExecutionMetrics)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_event(self, event: TaskTraceEvent) -> None:
        self.events.append(event)
        self.metrics.attempts_count += 1
        self.metrics.total_duration_ms += event.duration_ms

    def complete(self, status: str = "COMPLETED") -> None:
        self.end_time = datetime.now().isoformat()
        self.status = status

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "goal": self.goal,
            "mode": self.mode,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status,
            "events": [e.to_dict() for e in self.events],
            "metrics": self.metrics.to_dict(),
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def save_jsonl(self, file_path: str | Path) -> None:
        """Append trace line to a JSONL file."""
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(self.to_dict(), ensure_ascii=False) + "\n")
