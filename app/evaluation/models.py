"""
app/evaluation/models.py

Data models for AURA's benchmark and research evaluation framework.
Provides structured abstractions for scenarios, scenario execution results,
and comprehensive multi-dimensional metric reports.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class BenchmarkCategory(str, Enum):
    """Evaluation categories across the whole-PC assistant intelligence stack."""
    DESKTOP = "desktop"
    BROWSER = "browser"
    FILESYSTEM = "filesystem"
    PERCEPTION = "perception"
    AGENT = "agent"
    CONTENT = "content"
    TUTORING = "tutoring"


@dataclass
class BenchmarkScenario:
    """Definition of a reproducible evaluation benchmark scenario."""
    scenario_id: str
    category: BenchmarkCategory
    user_command: str
    description: str = ""
    expected_environment: str = "desktop"
    expected_action_sequence: list[str] = field(default_factory=list)
    expected_final_state: dict[str, Any] = field(default_factory=dict)
    expected_mode: str = "DO_IT_FOR_ME"  # "DO_IT_FOR_ME" | "SHOW_ME_HOW"
    timeout_sec: float = 10.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "category": self.category.value,
            "user_command": self.user_command,
            "description": self.description,
            "expected_environment": self.expected_environment,
            "expected_action_sequence": self.expected_action_sequence,
            "expected_final_state": self.expected_final_state,
            "expected_mode": self.expected_mode,
            "timeout_sec": self.timeout_sec,
            "metadata": self.metadata,
        }


@dataclass
class ScenarioResult:
    """Outcome and execution telemetry for an individual benchmark scenario."""
    scenario_id: str
    category: str
    status: str  # "PASSED" | "FAILED" | "SKIPPED"
    duration_ms: float = 0.0
    attempts: int = 1
    verification_passed: bool = False
    grounding_accurate: bool = True
    recovery_occurred: bool = False
    recovery_success: bool = False
    replan_count: int = 0
    user_intervention: bool = False
    tutoring_completed: bool = False
    content_extraction_success: bool = True
    content_qa_grounded: bool = True
    failure_type: str | None = None
    error: str | None = None
    trace_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MetricReport:
    """Quantitative performance, accuracy, and reliability metrics."""
    total_scenarios: int = 0
    passed_scenarios: int = 0
    failed_scenarios: int = 0
    task_success_rate: float = 0.0
    verification_accuracy: float = 0.0
    target_grounding_accuracy: float = 0.0
    recovery_success_rate: float = 0.0
    average_attempts_per_task: float = 0.0
    average_duration_ms: float = 0.0
    replanning_rate: float = 0.0
    user_intervention_rate: float = 0.0
    tutoring_completion_rate: float = 0.0
    content_extraction_success_rate: float = 0.0
    content_qa_grounding_rate: float = 0.0
    category_breakdown: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_markdown_table(self) -> str:
        """Format metrics as a clean Markdown table."""
        return (
            "| Metric | Value |\n"
            "|---|---|\n"
            f"| **Total Scenarios** | {self.total_scenarios} |\n"
            f"| **Task Success Rate** | {self.task_success_rate * 100:.1f}% ({self.passed_scenarios}/{self.total_scenarios}) |\n"
            f"| **Verification Accuracy** | {self.verification_accuracy * 100:.1f}% |\n"
            f"| **Target Grounding Accuracy** | {self.target_grounding_accuracy * 100:.1f}% |\n"
            f"| **Recovery Success Rate** | {self.recovery_success_rate * 100:.1f}% |\n"
            f"| **Average Attempts/Task** | {self.average_attempts_per_task:.2f} |\n"
            f"| **Average Task Duration** | {self.average_duration_ms:.1f} ms |\n"
            f"| **Replanning Rate** | {self.replanning_rate * 100:.1f}% |\n"
            f"| **User Intervention Rate** | {self.user_intervention_rate * 100:.1f}% |\n"
            f"| **Tutoring Completion Rate** | {self.tutoring_completion_rate * 100:.1f}% |\n"
            f"| **Content Extraction Rate** | {self.content_extraction_success_rate * 100:.1f}% |\n"
            f"| **Content QA Grounding Rate** | {self.content_qa_grounding_rate * 100:.1f}% |\n"
        )


@dataclass
class BenchmarkResult:
    """Aggregated outcome of an evaluation run across all benchmark scenarios."""
    run_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    aura_version: str = "1.0.0"
    metrics: MetricReport = field(default_factory=MetricReport)
    scenario_results: list[ScenarioResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "aura_version": self.aura_version,
            "metrics": self.metrics.to_dict(),
            "scenario_results": [r.to_dict() for r in self.scenario_results],
        }

    def save_json(self, file_path: str | Path) -> None:
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
