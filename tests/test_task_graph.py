"""
Tests for TaskGraph, TaskNode, dependencies, and topological scheduling.
"""

from __future__ import annotations

import pytest

from app.intelligence.action import Action, ActionType
from app.intelligence.task_graph import NodeStatus, TaskGraph, TaskNode


class TestTaskGraph:
    def test_node_creation_and_lookup(self):
        graph = TaskGraph(goal="Test Goal")
        node1 = TaskNode(
            task_id="t1",
            description="Launch Notepad",
            action=Action(action_type=ActionType.LAUNCH_APPLICATION, target="notepad"),
        )
        graph.add_node(node1)

        assert len(graph) == 1
        assert "t1" in graph
        assert graph.get_node("t1") == node1
        assert node1.status == NodeStatus.PENDING

    def test_dependencies_ready_and_blocked(self):
        graph = TaskGraph(goal="Create folder and move file")
        t1 = TaskNode(task_id="t1", description="Open Downloads")
        t2 = TaskNode(task_id="t2", description="Create AURA folder", dependencies=["t1"])
        t3 = TaskNode(task_id="t3", description="Locate report.docx", dependencies=["t1"])
        t4 = TaskNode(task_id="t4", description="Move report to AURA", dependencies=["t2", "t3"])

        for n in (t1, t2, t3, t4):
            graph.add_node(n)

        # Initially, only t1 is ready; t2, t3, t4 are blocked
        ready = graph.get_ready_nodes()
        assert len(ready) == 1
        assert ready[0].task_id == "t1"

        blocked = graph.get_blocked_nodes()
        assert len(blocked) == 3

        # Complete t1 -> t2 and t3 should become ready
        graph.mark_completed("t1")
        ready2 = graph.get_ready_nodes()
        ready_ids = {n.task_id for n in ready2}
        assert ready_ids == {"t2", "t3"}

        # Complete t2 only -> t4 is still blocked by t3
        graph.mark_completed("t2")
        assert not graph.can_execute("t4")

        # Complete t3 -> t4 is ready
        graph.mark_completed("t3")
        assert graph.can_execute("t4")
        ready3 = graph.get_ready_nodes()
        assert len(ready3) == 1
        assert ready3[0].task_id == "t4"

    def test_failure_propagation(self):
        graph = TaskGraph()
        t1 = TaskNode(task_id="t1")
        t2 = TaskNode(task_id="t2", dependencies=["t1"])
        t3 = TaskNode(task_id="t3", dependencies=["t2"])

        for n in (t1, t2, t3):
            graph.add_node(n)

        graph.mark_failed("t1", failure_info={"error": "Launch failed"})
        assert graph.get_node("t1").status == NodeStatus.FAILED
        assert graph.get_node("t2").status == NodeStatus.BLOCKED
        assert graph.is_failed() is True

    def test_cancellation(self):
        graph = TaskGraph()
        t1 = TaskNode(task_id="t1")
        t2 = TaskNode(task_id="t2", dependencies=["t1"])

        graph.add_node(t1)
        graph.add_node(t2)

        graph.cancel()
        assert t1.status == NodeStatus.CANCELLED
        assert t2.status == NodeStatus.CANCELLED
        assert graph.is_cancelled() is True

    def test_topological_sort(self):
        graph = TaskGraph()
        t1 = TaskNode(task_id="t1")
        t2 = TaskNode(task_id="t2", dependencies=["t1"])
        t3 = TaskNode(task_id="t3", dependencies=["t2"])

        graph.add_node(t3)
        graph.add_node(t1)
        graph.add_node(t2)

        sorted_nodes = graph.topological_sort()
        ids = [n.task_id for n in sorted_nodes]
        assert ids == ["t1", "t2", "t3"]

    def test_cycle_detection(self):
        graph = TaskGraph()
        t1 = TaskNode(task_id="t1", dependencies=["t2"])
        t2 = TaskNode(task_id="t2", dependencies=["t1"])
        graph.add_node(t1)
        graph.add_node(t2)

        with pytest.raises(ValueError, match="cycle"):
            graph.topological_sort()
