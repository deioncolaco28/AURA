"""
app/intelligence/planner.py

Converts interpreted intent into structured Task and TaskGraph models for AURA.
"""

from __future__ import annotations

from app.config.constants import AssistantMode
from app.intelligence.action import Action, ActionType
from app.intelligence.expected_state import ExpectedState
from app.intelligence.intent import Intent
from app.intelligence.task import Task
from app.intelligence.task_decomposer import (
    RuleBasedTaskDecomposer,
    TaskDecomposer,
)
from app.intelligence.task_graph import NodeStatus, TaskGraph, TaskNode


class Planner:
    """
    Converts interpreted intent into a structured Task and TaskGraph.

    Planning responsibility is separated from task decomposition:
    
        Intent
          ↓
        Planner
          ↓
        TaskDecomposer
          ↓
        Actions / TaskGraph
          ↓
        Task
    """

    def __init__(
        self,
        decomposer: TaskDecomposer | None = None,
    ):
        self.decomposer = (
            decomposer
            or RuleBasedTaskDecomposer()
        )

    def create_task(
        self,
        intent: Intent,
    ) -> Task:
        """Create a task from an interpreted intent."""
        task = Task(
            goal=intent.goal,
            mode=intent.mode,
            risk_level=intent.risk_level,
            requires_confirmation=intent.requires_confirmation,
        )

        actions = self.generate_actions(
            intent
        )

        for action in actions:
            task.add_action(action)

        return task

    def generate_actions(
        self,
        intent: Intent,
    ) -> list[Action]:
        """
        Ask the configured decomposer to generate
        an ordered action sequence.
        """
        return self.decomposer.decompose(
            goal=intent.goal,
            mode=intent.mode,
        )

    def create_task_graph(self, intent: Intent | Task) -> TaskGraph:
        """
        Build a TaskGraph with dependencies and expected states from an Intent or Task.
        """
        if isinstance(intent, Intent):
            task = self.create_task(intent)
        else:
            task = intent

        graph = TaskGraph(goal=task.goal)

        for idx, action in enumerate(task.actions, start=1):
            task_id = action.action_id or f"step_{idx}"
            env = self._infer_environment(action.action_type)
            expected = self._infer_expected_state(action)

            node = TaskNode(
                task_id=task_id,
                description=action.description or f"{action.action_type} {action.target or ''}".strip(),
                action=action,
                dependencies=list(action.dependencies),
                environment=env,
                target_query=action.target,
                expected_state=expected,
                status=NodeStatus.PENDING,
            )
            graph.add_node(node)

        return graph

    @staticmethod
    def _infer_environment(action_type: str) -> str:
        """Infer target environment category from action type."""
        if action_type in (
            ActionType.LAUNCH_APPLICATION,
            ActionType.FOCUS_APPLICATION,
            ActionType.CLOSE_APPLICATION,
            ActionType.SWITCH_APPLICATION,
            ActionType.MINIMIZE_WINDOW,
            ActionType.MAXIMIZE_WINDOW,
            ActionType.RESTORE_WINDOW,
        ):
            return "application"

        if action_type in (
            ActionType.OPEN_URL,
            ActionType.NAVIGATE_URL,
            ActionType.BROWSER_BACK,
            ActionType.BROWSER_FORWARD,
            ActionType.BROWSER_REFRESH,
            ActionType.OPEN_TAB,
            ActionType.CLOSE_TAB,
            ActionType.SWITCH_TAB,
            ActionType.SUBMIT_FORM,
            ActionType.EXTRACT_PAGE_CONTENT,
        ):
            return "browser"

        if action_type in (
            ActionType.CREATE_FILE,
            ActionType.CREATE_FOLDER,
            ActionType.READ_FILE,
            ActionType.WRITE_FILE,
            ActionType.LIST_FILES,
            ActionType.SEARCH_FILES,
            ActionType.OPEN_FILE,
            ActionType.COPY_FILE,
            ActionType.MOVE_FILE,
            ActionType.RENAME_FILE,
            ActionType.DELETE_FILE,
            ActionType.COMPRESS_FILES,
            ActionType.EXTRACT_ARCHIVE,
        ):
            return "filesystem"

        return "desktop"

    @staticmethod
    def _infer_expected_state(action: Action) -> ExpectedState:
        """Convert Action.verification spec or Action semantics to an ExpectedState."""
        v = action.verification or {}
        vtype = str(v.get("type", "")).upper()

        expected = ExpectedState()

        if vtype == "APPLICATION_RUNNING":
            procs = v.get("processes") or ([v["process"]] if "process" in v else [action.target])
            expected.app_running = procs
        elif vtype == "APPLICATION_FOREGROUND":
            expected.app_foreground = v.get("app_name") or action.target
        elif vtype == "BROWSER_URL":
            expected.browser_url_contains = v.get("url") or action.target
        elif vtype in ("FS_EXISTS", "FILE_EXISTS", "FOLDER_EXISTS"):
            expected.file_exists = v.get("path") or action.target
        elif vtype in ("FS_DELETED", "FILE_DELETED"):
            expected.file_deleted = v.get("path") or action.target
        elif vtype in ("FS_MOVED", "FILE_MOVED"):
            expected.file_moved = (v.get("source", action.target), v.get("destination", str(action.value)))
        elif vtype in ("SCREEN_CONTAINS_TEXT", "TEXT_VISIBLE"):
            expected.text_visible = v.get("text", action.target)
        elif vtype == "SCREEN_CHANGED":
            expected.screen_changed = True

        return expected