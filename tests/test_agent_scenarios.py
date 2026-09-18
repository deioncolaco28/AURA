"""
Integration tests for Phase 4 Agent Intelligence Scenarios.
"""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from app.config.constants import AssistantMode, AssistantState
from app.core.agent import Agent
from app.core.execution_engine import ExecutionEngine
from app.core.failure import FailureType
from app.core.observation import ScreenObservation
from app.core.rule_based_replanner import RuleBasedReplanner
from app.intelligence.action import Action, ActionType
from app.intelligence.expected_state import ExpectedState
from app.intelligence.intent import Intent
from app.intelligence.planner import Planner
from app.intelligence.task_graph import NodeStatus, TaskGraph, TaskNode


class TestAgentScenarios:
    def test_scenario_1_open_notepad(self):
        # Scenario 1: "Open Notepad" -> Launch -> Verify -> Complete
        mock_executor = MagicMock()
        mock_executor.execute.side_effect = lambda act: act
        mock_app_verifier = MagicMock()
        mock_app_verifier.verify.return_value = True

        agent = Agent(
            action_executor=mock_executor,
            application_verifier=mock_app_verifier,
        )

        ctx = agent.process_text("open notepad")
        assert ctx is not None
        assert ctx.completed is True
        assert agent.state.current_state == AssistantState.COMPLETED

    def test_scenario_2_conditional_chrome(self):
        # Scenario 2: Conditional Task: If Chrome open, use it; otherwise open it
        graph = TaskGraph(goal="Use or open Chrome")
        
        # Node with condition: skip launch if already open
        from app.intelligence.task_condition import ConditionType, TaskCondition
        node = TaskNode(
            task_id="launch_chrome",
            action=Action(action_type=ActionType.LAUNCH_APPLICATION, target="chrome"),
            condition=TaskCondition(condition_type=ConditionType.APP_IS_OPEN, target="chrome.exe"),
        )
        graph.add_node(node)

        mock_observer = MagicMock()
        mock_observer.observe.return_value = ScreenObservation(processes=["chrome.exe"])

        engine = ExecutionEngine(
            execute_action=lambda a: a,
            verify_action=lambda a: None,
            observer=mock_observer,
        )

        ctx = engine.run_graph(graph)
        # Node should be marked SKIPPED because chrome was already open
        assert graph.get_node("launch_chrome").status == NodeStatus.SKIPPED
        assert graph.is_completed() is True

    def test_scenario_3_create_folder_and_move_file(self, tmp_path):
        # Scenario 3: Create AURA folder and move report.docx into it
        src_file = tmp_path / "report.docx"
        src_file.write_text("Test Report Content")
        dst_folder = tmp_path / "AURA"

        graph = TaskGraph(goal="Create folder and move file")
        t1 = TaskNode(
            task_id="create_folder",
            action=Action(action_type=ActionType.CREATE_FOLDER, target=str(dst_folder)),
            expected_state=ExpectedState(folder_exists=str(dst_folder)),
        )
        t2 = TaskNode(
            task_id="move_file",
            action=Action(action_type=ActionType.MOVE_FILE, target=str(src_file), value=str(dst_folder)),
            dependencies=["create_folder"],
            expected_state=ExpectedState(file_moved=(str(src_file), str(dst_folder / "report.docx"))),
        )
        graph.add_node(t1)
        graph.add_node(t2)

        from app.automation.filesystem_manager import FileSystemManager
        fs = FileSystemManager()

        def _exec(action: Action) -> Action:
            if action.action_type == ActionType.CREATE_FOLDER:
                fs.create_folder(action.target)
            elif action.action_type == ActionType.MOVE_FILE:
                fs.move_path(action.target, str(dst_folder / "report.docx"))
            return action

        engine = ExecutionEngine(
            execute_action=_exec,
            verify_action=lambda a: None,
        )

        ctx = engine.run_graph(graph)
        assert graph.is_completed() is True
        assert dst_folder.exists()
        assert (dst_folder / "report.docx").exists()
        assert not src_file.exists()

    def test_scenario_4_context_entity_chaining(self):
        # Scenario 4: Browser search -> Extract -> Store in context -> Paste in Notepad
        graph = TaskGraph(goal="Search and paste")
        t1 = TaskNode(
            task_id="extract_web",
            action=Action(action_type=ActionType.EXTRACT_PAGE_CONTENT, target="search_result"),
        )
        t2 = TaskNode(
            task_id="paste_notepad",
            action=Action(action_type=ActionType.TYPE_TEXT, value="$extracted_text"),
            dependencies=["extract_web"],
        )
        graph.add_node(t1)
        graph.add_node(t2)

        executed_types = []

        def _exec(action: Action) -> Action:
            if action.action_type == ActionType.EXTRACT_PAGE_CONTENT:
                action.execution_result = {"extracted_text": "AURA Intelligence Summary"}
            elif action.action_type == ActionType.TYPE_TEXT:
                executed_types.append(action.value)
            return action

        engine = ExecutionEngine(
            execute_action=_exec,
            verify_action=lambda a: None,
        )

        ctx = engine.run_graph(graph)
        assert graph.is_completed() is True
        assert executed_types == ["AURA Intelligence Summary"]

    def test_scenario_5_target_missing_recovery(self):
        # Scenario 5: Target missing -> Replanner re-grounds
        from app.perception.ui_element import UIElement
        mock_ranker = MagicMock()
        mock_best = MagicMock()
        mock_best.score = 0.9
        mock_best.reason = "Text match"
        mock_best.element = UIElement(
            element_id="btn_save",
            element_type="button",
            text="Save",
            x=100,
            y=200,
            width=50,
            height=30,
        )
        mock_ranker.rank.return_value = MagicMock(found=True, best=mock_best)

        replanner = RuleBasedReplanner(target_ranker=mock_ranker)

        obs = ScreenObservation(elements=[mock_best.element])
        mock_obs_engine = MagicMock()
        mock_obs_engine.observe.return_value = obs

        attempts = []

        def _exec(action: Action) -> Action:
            attempts.append(action)
            if len(attempts) <= 2:
                raise RuntimeError("Target not found on screen.")
            return action

        engine = ExecutionEngine(
            execute_action=_exec,
            verify_action=lambda a: None,
            replanner=replanner,
            observer=mock_obs_engine,
            max_replans=1,
            max_retries=1,
        )

        task_act = Action(action_type=ActionType.CLICK, target="Save")
        from app.intelligence.task import Task
        task = Task(goal="Click Save")
        task.add_action(task_act)

        ctx = engine.run(task)
        assert ctx.completed is True
        assert len(attempts) == 3
        assert attempts[2].resolved is True
        assert attempts[2].parameters["x"] == 125

    def test_scenario_6_application_closes_recovery(self):
        # Scenario 6: App closes unexpectedly -> Recovery re-launches and continues
        graph = TaskGraph(goal="Type in Notepad")
        t1 = TaskNode(
            task_id="type_text",
            action=Action(action_type=ActionType.TYPE_TEXT, target="Notepad", value="Hello"),
        )
        graph.add_node(t1)

        from app.core.failure import FailureInfo
        failure = FailureInfo(
            action=t1.action,
            failure_type=FailureType.APPLICATION_NOT_RUNNING,
            metadata={"app_name": "Notepad"},
        )

        from app.core.recovery_engine import RecoveryEngine
        rec = RecoveryEngine()
        plan = rec.plan_recovery(failure)
        assert plan.strategy.value == "GLOBAL_REPLAN"
        assert len(plan.actions) == 3
        assert plan.actions[0].action_type == ActionType.LAUNCH_APPLICATION
        assert plan.actions[0].target == "Notepad"

    def test_scenario_7_ambiguous_target_asks_user(self):
        # Scenario 7: Ambiguous target -> Do NOT click, ask user
        from app.core.failure import FailureInfo
        act = Action(action_type=ActionType.CLICK, target="Delete")
        failure = FailureInfo(
            action=act,
            failure_type=FailureType.TARGET_AMBIGUOUS,
            metadata={"clarification_question": "Did you mean Delete File or Delete Folder?"},
        )

        from app.core.recovery_engine import RecoveryEngine
        rec = RecoveryEngine()
        plan = rec.plan_recovery(failure)
        assert plan.strategy.value == "ASK_USER"
        assert plan.can_continue is False
        assert len(plan.actions) == 1
        assert plan.actions[0].action_type == ActionType.SPEAK
        assert "Did you mean Delete File" in plan.actions[0].value

    def test_scenario_8_cancellation(self):
        # Scenario 8: User cancels -> transition to CANCELLED / IDLE immediately
        mock_voice = MagicMock()
        agent = Agent(voice_manager=mock_voice)

        res = agent.process_text("stop")
        assert res is None
        mock_voice.speak.assert_called_with("Task cancelled.")
