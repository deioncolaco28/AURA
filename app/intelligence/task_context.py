"""
app/intelligence/task_context.py

Task-scoped contextual memory and entity reference resolution for AURA.
Tracks discovered files, URLs, extracted text, active application/window context,
and provides deterministic resolution of context variables (e.g. $report, $folder, 'it').
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskContext:
    """
    Task-scoped runtime context.
    Short-lived: created at goal start, cleared on completion/failure/cancellation.
    """

    goal: str = ""
    current_task_id: str | None = None
    current_environment: str = "desktop"
    foreground_app: str | None = None
    active_window: str | None = None
    browser_url: str | None = None

    # Discovered entities: e.g. {"report": "C:/Downloads/report.docx", "folder": "C:/Downloads/AURA"}
    entities: dict[str, Any] = field(default_factory=dict)

    # Intermediate execution results: {task_id: {key: value}}
    intermediate_results: dict[str, Any] = field(default_factory=dict)

    # Lifecycle tracking
    completed_tasks: list[str] = field(default_factory=list)
    pending_tasks: list[str] = field(default_factory=list)
    failures: list[Any] = field(default_factory=list)
    user_clarifications: dict[str, str] = field(default_factory=dict)

    # Structured execution history/traces
    history: list[dict[str, Any]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def set_entity(self, name: str, value: Any) -> None:
        """Register a discovered entity (normalizing leading '$' if present)."""
        key = name.lstrip("$").lower()
        self.entities[key] = value

    def get_entity(self, name: str, default: Any = None) -> Any:
        """Retrieve an entity by name."""
        key = name.lstrip("$").lower()
        return self.entities.get(key, default)

    def has_entity(self, name: str) -> bool:
        """Check if an entity exists in context."""
        key = name.lstrip("$").lower()
        return key in self.entities

    def store_result(self, task_id: str, key: str, value: Any) -> None:
        """Store an intermediate result from a task node."""
        if task_id not in self.intermediate_results:
            self.intermediate_results[task_id] = {}
        self.intermediate_results[task_id][key] = value

    def get_result(self, task_id: str, key: str, default: Any = None) -> Any:
        """Retrieve an intermediate result from a task node."""
        return self.intermediate_results.get(task_id, {}).get(key, default)

    def record_completed(self, task_id: str) -> None:
        """Record task completion and update tracking lists."""
        if task_id not in self.completed_tasks:
            self.completed_tasks.append(task_id)
        if task_id in self.pending_tasks:
            self.pending_tasks.remove(task_id)

    def record_failure(self, failure_info: Any) -> None:
        """Record a failure event."""
        self.failures.append(failure_info)

    def clear(self) -> None:
        """Reset task context on workflow termination."""
        self.goal = ""
        self.current_task_id = None
        self.entities.clear()
        self.intermediate_results.clear()
        self.completed_tasks.clear()
        self.pending_tasks.clear()
        self.failures.clear()
        self.user_clarifications.clear()
        self.history.clear()
        self.metadata.clear()


class EntityResolver:
    """
    Deterministic resolver for contextual entities ($var, 'it', 'that', 'this file', ordinal references).
    """

    def __init__(self, context: TaskContext | None = None):
        self.context = context or TaskContext()

    def resolve(self, target_or_text: str | None) -> str | None:
        """
        Resolve entity references in a string.
        Examples:
        - "$report" -> "C:/Users/.../report.docx"
        - "move $report to $aura_folder" -> "move C:/.../report.docx to C:/.../AURA"
        - "it" / "that" -> most recently registered entity
        """
        if target_or_text is None:
            return None

        text = str(target_or_text)

        # 1. Resolve explicit $variables: $var or ${var}
        def _replace_var(match):
            var_name = match.group(1) or match.group(2)
            val = self.context.get_entity(var_name)
            if val is not None:
                return str(val)
            return match.group(0)

        pattern = r"\$\{([a-zA-Z0-9_]+)\}|\$([a-zA-Z0-9_]+)"
        resolved = re.sub(pattern, _replace_var, text)

        # 2. Resolve contextual pronouns if target is literally 'it', 'that', 'this file', 'the file'
        normalized = resolved.strip().lower()
        if normalized in ("it", "that", "this file", "the file", "this"):
            # Check for file entities first
            for key in ("file", "report", "document", "target", "last_entity"):
                if self.context.has_entity(key):
                    return str(self.context.get_entity(key))
            # Fallback to the most recent entity if only one or two exist
            if self.context.entities:
                return str(list(self.context.entities.values())[-1])

        return resolved
