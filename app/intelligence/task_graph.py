"""
app/intelligence/task_graph.py

Graph representation of multi-step agent tasks with explicit dependencies,
prerequisites, node states, and deterministic topological scheduling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from app.intelligence.action import Action


class NodeStatus(str, Enum):
    """Execution status for a task node in the task graph."""

    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


@dataclass
class TaskNode:
    """Represents a single executable node within a TaskGraph."""

    task_id: str
    description: str = ""
    action: Action | None = None
    dependencies: list[str] = field(default_factory=list)
    environment: str = "desktop"
    target_query: str | None = None
    expected_state: Any = None  # ExpectedState instance or dict
    condition: Any = None       # TaskCondition instance or Callable
    status: NodeStatus = NodeStatus.PENDING
    attempts: int = 0
    max_attempts: int = 2
    failure_info: Any = None
    recovery_strategy: str | None = None
    result: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        """Return True if the node is in a terminal state."""
        return self.status in (
            NodeStatus.COMPLETED,
            NodeStatus.FAILED,
            NodeStatus.SKIPPED,
            NodeStatus.CANCELLED,
        )

    @property
    def is_successful(self) -> bool:
        """Return True if node completed or was skipped (considered satisfied)."""
        return self.status in (NodeStatus.COMPLETED, NodeStatus.SKIPPED)


class TaskGraph:
    """
    Directed Acyclic Graph (DAG) of task nodes with dependency tracking,
    cycle detection, state propagation, and ready node scheduling.
    """

    def __init__(self, goal: str = ""):
        self.goal = goal
        self._nodes: dict[str, TaskNode] = {}
        self.metadata: dict[str, Any] = {}

    def add_node(self, node: TaskNode) -> TaskNode:
        """Add a node to the graph."""
        if not node.task_id:
            raise ValueError("TaskNode must have a non-empty task_id.")
        self._nodes[node.task_id] = node
        return node

    def get_node(self, task_id: str) -> TaskNode | None:
        """Retrieve a node by its task_id."""
        return self._nodes.get(task_id)

    @property
    def nodes(self) -> list[TaskNode]:
        """Return list of all task nodes."""
        return list(self._nodes.values())

    def __len__(self) -> int:
        return len(self._nodes)

    def __contains__(self, task_id: str) -> bool:
        return task_id in self._nodes

    def get_ready_nodes(self) -> list[TaskNode]:
        """
        Return nodes that are ready to execute:
        - status is PENDING or READY
        - all prerequisite dependencies are COMPLETED (or SKIPPED).
        """
        ready: list[TaskNode] = []
        for node in self._nodes.values():
            if node.status in (NodeStatus.PENDING, NodeStatus.READY):
                if self.can_execute(node.task_id):
                    node.status = NodeStatus.READY
                    ready.append(node)
                else:
                    node.status = NodeStatus.BLOCKED
        return ready

    def get_blocked_nodes(self) -> list[TaskNode]:
        """Return nodes that are blocked because prerequisites are not yet met."""
        blocked: list[TaskNode] = []
        for node in self._nodes.values():
            if node.status in (NodeStatus.PENDING, NodeStatus.BLOCKED):
                if not self.can_execute(node.task_id):
                    node.status = NodeStatus.BLOCKED
                    blocked.append(node)
        return blocked

    def can_execute(self, task_id: str) -> bool:
        """Return True if all dependencies of the node are completed/skipped."""
        node = self.get_node(task_id)
        if not node:
            return False
        for dep_id in node.dependencies:
            dep_node = self.get_node(dep_id)
            if not dep_node or not dep_node.is_successful:
                return False
        return True

    def mark_running(self, task_id: str) -> None:
        """Mark a node as currently running."""
        node = self.get_node(task_id)
        if node:
            node.status = NodeStatus.RUNNING
            node.attempts += 1

    def mark_completed(self, task_id: str, result: dict[str, Any] | None = None) -> None:
        """Mark a node as successfully completed."""
        node = self.get_node(task_id)
        if node:
            node.status = NodeStatus.COMPLETED
            if result:
                node.result.update(result)
            self._update_graph_statuses()

    def mark_failed(self, task_id: str, failure_info: Any = None) -> None:
        """Mark a node as failed and block dependent tasks."""
        node = self.get_node(task_id)
        if node:
            node.status = NodeStatus.FAILED
            node.failure_info = failure_info
            self._propagate_failure(task_id)

    def mark_skipped(self, task_id: str, reason: str = "") -> None:
        """Mark a node as skipped (e.g. condition already satisfied / idempotent)."""
        node = self.get_node(task_id)
        if node:
            node.status = NodeStatus.SKIPPED
            node.metadata["skip_reason"] = reason
            self._update_graph_statuses()

    def cancel(self) -> None:
        """Cancel all pending, ready, or running nodes in the graph."""
        for node in self._nodes.values():
            if not node.is_terminal:
                node.status = NodeStatus.CANCELLED

    def is_completed(self) -> bool:
        """Return True if all nodes have completed or been skipped."""
        if not self._nodes:
            return True
        return all(node.is_successful for node in self._nodes.values())

    def is_failed(self) -> bool:
        """Return True if any node has failed without recovery."""
        return any(node.status == NodeStatus.FAILED for node in self._nodes.values())

    def is_cancelled(self) -> bool:
        """Return True if the graph execution was cancelled."""
        return any(node.status == NodeStatus.CANCELLED for node in self._nodes.values())

    def topological_sort(self) -> list[TaskNode]:
        """
        Return nodes in topological order based on dependencies.
        Raises ValueError if a dependency cycle is detected.
        """
        in_degree: dict[str, int] = {k: 0 for k in self._nodes}
        adj: dict[str, list[str]] = {k: [] for k in self._nodes}

        for node_id, node in self._nodes.items():
            for dep in node.dependencies:
                if dep in adj:
                    adj[dep].append(node_id)
                    in_degree[node_id] += 1

        queue = [node_id for node_id, deg in in_degree.items() if deg == 0]
        sorted_nodes: list[TaskNode] = []

        while queue:
            curr = queue.pop(0)
            sorted_nodes.append(self._nodes[curr])
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_nodes) != len(self._nodes):
            raise ValueError("TaskGraph contains a dependency cycle.")

        return sorted_nodes

    def _propagate_failure(self, failed_node_id: str) -> None:
        """Recursively mark direct and indirect dependents as BLOCKED."""
        for node in self._nodes.values():
            if failed_node_id in node.dependencies and node.status in (NodeStatus.PENDING, NodeStatus.READY):
                node.status = NodeStatus.BLOCKED

    def _update_graph_statuses(self) -> None:
        """Update readiness of downstream nodes after status changes."""
        for node in self._nodes.values():
            if node.status == NodeStatus.BLOCKED and self.can_execute(node.task_id):
                node.status = NodeStatus.READY
