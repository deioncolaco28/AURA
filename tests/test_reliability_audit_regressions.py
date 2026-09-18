"""
tests/test_reliability_audit_regressions.py

Regression test suite for full-system engineering audit & reliability hardening pass.
Verifies root-cause fixes:
1. 'time' import and bounded launch lifecycles
2. Application resolution for Chrome, Edge, Terminal, Notepad, Calculator, Explorer
3. Idempotency & duplicate launch prevention
4. Non-retryable error classification and retry loop breaking
5. Unsupported command truthful failure handling (no false success reporting)
6. Conversational / Capability request routing without fake automation
7. Terminal aliases & natural-language parsing
8. Multi-step open + type + save workflows and standalone save
9. Cancellation and recovery safety
"""

import os
from unittest.mock import MagicMock, patch
import pytest

from app.automation.action_executor import ActionExecutor
from app.automation.application_manager import ApplicationManager
from app.automation.applications import ApplicationController
from app.config.constants import AssistantMode, AssistantState
from app.core.agent import Agent
from app.core.execution import ExecutionContext, ExecutionStep
from app.core.execution_engine import ExecutionEngine
from app.core.failure import FailureClassifier, FailureType
from app.intelligence.action import Action, ActionType
from app.intelligence.intent import Intent
from app.intelligence.planner import Planner
from app.intelligence.task import Task
from app.intelligence.task_decomposer import RuleBasedTaskDecomposer, TaskDecomposer


# ==============================================================================
# 1. APPLICATION RESOLUTION REGRESSIONS
# ==============================================================================

class TestApplicationResolutionRegressions:
    """Verify robust multi-tier resolution across all registered apps."""

    def test_chrome_resolution_multi_tier(self):
        controller = ApplicationController()
        # Should resolve without raising FileNotFoundError / ValueError
        resolved = controller.resolve("chrome")
        assert resolved is not None
        assert "chrome" in resolved.lower()

    def test_chrome_aliases(self):
        controller = ApplicationController()
        for alias in ("google chrome", "chrome", "CHROME"):
            resolved = controller.resolve(alias)
            assert resolved is not None
            assert "chrome" in resolved.lower()

    def test_terminal_resolution_and_aliases(self):
        controller = ApplicationController()
        for term_alias in ("terminal", "the terminal", "windows terminal", "cmd", "command prompt", "powershell"):
            resolved = controller.resolve(term_alias)
            assert resolved is not None
            assert any(k in resolved.lower() for k in ("wt", "cmd", "powershell"))

    def test_edge_resolution(self):
        controller = ApplicationController()
        resolved = controller.resolve("edge")
        assert resolved is not None
        assert "edge" in resolved.lower()

    def test_notepad_and_calc_resolution(self):
        controller = ApplicationController()
        assert "notepad" in controller.resolve("notepad").lower()
        assert "calc" in controller.resolve("calculator").lower()
        assert "calc" in controller.resolve("calc").lower()

    def test_application_manager_terminal_entry(self):
        am = ApplicationManager()
        entry = am.resolve_application("terminal")
        assert entry is not None
        assert entry.logical_name == "Terminal"

        entry_the = am.resolve_application("the terminal")
        assert entry_the is not None
        assert entry_the.logical_name == "Terminal"

        entry_cmd = am.resolve_application("cmd")
        assert entry_cmd is not None
        assert entry_cmd.logical_name == "Command Prompt"


# ==============================================================================
# 2. DUPLICATE PREVENTION & IDEMPOTENCY REGRESSIONS
# ==============================================================================

class TestDuplicatePreventionRegressions:
    """Verify that launching an already-running app focuses it rather than duplicating."""

    def test_launch_application_focuses_if_already_running(self):
        mock_controller = MagicMock()
        mock_app_mgr = MagicMock()
        mock_app_mgr.is_running.return_value = True

        executor = ActionExecutor(
            controller=mock_controller,
            application_manager=mock_app_mgr,
        )

        action = Action(
            action_type=ActionType.LAUNCH_APPLICATION,
            target="notepad",
        )

        executor.execute(action)

        # Must focus existing instance
        mock_app_mgr.focus.assert_called_once_with("notepad")
        # Must NOT call launch on controller
        mock_controller.launch_application.assert_not_called()
        assert action.execution_result.get("idempotent_focus") is True

    def test_launch_application_launches_if_not_running(self):
        mock_controller = MagicMock()
        mock_app_mgr = MagicMock()
        mock_app_mgr.is_running.return_value = False

        executor = ActionExecutor(
            controller=mock_controller,
            application_manager=mock_app_mgr,
        )

        action = Action(
            action_type=ActionType.LAUNCH_APPLICATION,
            target="notepad",
            parameters={"startup_wait": 0.0},
        )

        executor.execute(action)

        # Must launch since it's not running
        mock_controller.launch_application.assert_called_once_with("notepad")


# ==============================================================================
# 3. NON-RETRYABLE ERROR SAFETY REGRESSIONS
# ==============================================================================

class TestNonRetryableErrorSafetyRegressions:
    """Verify programmer errors (NameError, TypeError, SyntaxError) never trigger retry loops."""

    def test_programmer_error_classified_as_non_recoverable(self):
        classifier = FailureClassifier()
        action = Action(action_type=ActionType.LAUNCH_APPLICATION, target="notepad")

        for err in (
            "NameError: name 'time' is not defined",
            "TypeError: 'NoneType' object is not callable",
            "SyntaxError: invalid syntax",
            "ImportError: No module named 'xyz'",
            "AttributeError: 'Action' object has no attribute 'abc'",
            "ValueError: Unsupported executable action: FOO",
        ):
            info = classifier.classify(action=action, error=err)
            assert info.recoverability is False, f"Expected {err} to be non-recoverable"

    def test_execution_engine_does_not_retry_programmer_error(self):
        call_count = 0

        def failing_action_executor(action):
            nonlocal call_count
            call_count += 1
            # Simulate a NameError like the previous bug
            raise NameError("name 'time' is not defined")

        engine = ExecutionEngine(
            execute_action=failing_action_executor,
            verify_action=MagicMock(),
            max_retries=5,  # even with 5 max retries
        )

        task = Task(goal="Open Notepad")
        task.add_action(Action(action_type=ActionType.LAUNCH_APPLICATION, target="notepad"))

        context = engine.run(task)

        # Must have executed exactly ONCE and then aborted without retrying 5 times!
        assert call_count == 1
        assert context.completed is False
        assert context.steps[0].status == "FAILED"


# ==============================================================================
# 4. FALSE SUCCESS REPORTING & INTENT ROUTING REGRESSIONS
# ==============================================================================

class TestIntentRoutingAndTruthfulReportingRegressions:
    """Verify truthful reporting for conversational, capability, and unsupported commands."""

    def test_unsupported_command_does_not_report_success(self):
        mock_voice = MagicMock()
        agent = Agent(voice_manager=mock_voice)

        result = agent.process_text("add for me")

        # Must fail truthfully, NOT report completed
        assert agent.state.current_state == AssistantState.FAILED
        assert result is None
        # Voice must speak unsupported message, NEVER 'Task completed.'
        spoken_calls = [c.args[0] for c in mock_voice.speak.call_args_list]
        assert any("not currently supported" in msg for msg in spoken_calls)
        assert not any("Task completed." == msg for msg in spoken_calls)

    def test_what_can_you_do_capability_query(self):
        mock_voice = MagicMock()
        agent = Agent(voice_manager=mock_voice)

        agent.process_text("what can you do")

        assert agent.state.current_state == AssistantState.IDLE
        spoken_calls = [c.args[0] for c in mock_voice.speak.call_args_list]
        assert any("I can help you" in msg for msg in spoken_calls)
        assert not any("Task completed." == msg for msg in spoken_calls)

    def test_greeting_query(self):
        mock_voice = MagicMock()
        agent = Agent(voice_manager=mock_voice)

        agent.process_text("hello")

        assert agent.state.current_state == AssistantState.IDLE
        spoken_calls = [c.args[0] for c in mock_voice.speak.call_args_list]
        assert any("Hello!" in msg for msg in spoken_calls)
        assert not any("Task completed." == msg for msg in spoken_calls)

    def test_cancellation_command(self):
        mock_voice = MagicMock()
        agent = Agent(voice_manager=mock_voice)

        agent.process_text("cancel")

        assert agent.state.current_state == AssistantState.IDLE
        mock_voice.speak.assert_called_with("Task cancelled.")


# ==============================================================================
# 5. NATURAL-LANGUAGE TASK DECOMPOSITION REGRESSIONS
# ==============================================================================

class TestTaskDecompositionRegressions:
    """Verify natural-language decomposition for multi-step, terminal, and save commands."""

    def test_terminal_command_variants(self):
        decomposer = RuleBasedTaskDecomposer()
        for cmd in ("open terminal", "open the terminal", "launch terminal", "start terminal", "open cmd", "open powershell"):
            actions = decomposer.decompose(cmd)
            assert len(actions) == 1
            assert actions[0].action_type == ActionType.LAUNCH_APPLICATION
            assert actions[0].target in ("terminal", "the terminal", "cmd", "powershell")

    def test_open_type_save_multi_step_decomposition(self):
        decomposer = RuleBasedTaskDecomposer()
        actions = decomposer.decompose("open Notepad and type hello Aura and save it as Aura")

        assert len(actions) == 5
        assert actions[0].action_type == ActionType.LAUNCH_APPLICATION
        assert actions[0].target == "notepad"
        assert actions[1].action_type == ActionType.TYPE_TEXT
        assert actions[1].value == "hello Aura"
        assert actions[2].action_type == ActionType.HOTKEY
        assert actions[2].parameters["keys"] == ["ctrl", "s"]
        assert actions[3].action_type == ActionType.TYPE_TEXT
        assert actions[3].value == "Aura.txt"
        assert actions[4].action_type == ActionType.PRESS_KEY
        assert actions[4].value == "enter"
        assert actions[4].verification["type"] == "FS_EXISTS"
        assert actions[4].verification["path"] == "Aura.txt"

    def test_standalone_save_it_as(self):
        decomposer = RuleBasedTaskDecomposer()
        actions = decomposer.decompose("save it as Aura")

        assert len(actions) == 3
        assert actions[0].action_type == ActionType.HOTKEY
        assert actions[1].action_type == ActionType.TYPE_TEXT
        assert actions[1].value == "Aura.txt"
        assert actions[2].action_type == ActionType.PRESS_KEY
        assert actions[2].value == "enter"

    def test_planner_creates_dag_with_dependencies_for_open_type_save(self):
        planner = Planner()
        intent = Intent(
            raw_text="open Notepad and type hello Aura and save it as Aura",
            goal="open Notepad and type hello Aura and save it as Aura",
        )
        graph = planner.create_task_graph(intent)

        assert len(graph) == 5
        # Verify dependencies in DAG
        nodes = {n.task_id: n for n in graph.nodes}
        assert "act_open_notepad" in nodes["act_type_text"].dependencies
        assert "act_type_text" in nodes["act_save_hotkey"].dependencies
        assert "act_save_hotkey" in nodes["act_save_filename"].dependencies
        assert "act_save_filename" in nodes["act_save_confirm"].dependencies


# ==============================================================================
# 6. SAVE FILENAME NORMALIZATION & EXTRACTION REGRESSIONS
# ==============================================================================

class TestSaveFilenameNormalizationRegressions:
    """Verify natural language spoken save filename extraction without article mangling."""

    def test_normalize_save_filename_variants(self):
        from app.intelligence.task_decomposer import normalize_save_filename

        cases = [
            ("save it as Aura", "Aura.txt"),
            ("save it as a Aura", "Aura.txt"),
            ("save it as an Aura", "Aura.txt"),
            ("save it as the Aura", "Aura.txt"),
            ("save it as Aura.txt", "Aura.txt"),
            ("save as Aura", "Aura.txt"),
            ("save as a Aura", "Aura.txt"),
            ("save the file as Aura", "Aura.txt"),
            ("save this as Aura", "Aura.txt"),
            ("save the document as Aura", "Aura.txt"),
            ("save it with the name Aura", "Aura.txt"),
            ("save it under the name Aura", "Aura.txt"),
            ("save it as a report", "report.txt"),
            ("save it as an important report", "important report.txt"),
            ("save the file as my notes.docx", "my notes.docx"),
            ("save as budget.xlsx", "budget.xlsx"),
            ("a Aura", "Aura.txt"),
            ("an Aura", "Aura.txt"),
            ("the Aura", "Aura.txt"),
        ]

        for spoken, expected in cases:
            result = normalize_save_filename(spoken, default_ext=".txt")
            assert result == expected, f"Failed for input '{spoken}': got '{result}', expected '{expected}'"

    def test_open_type_save_with_spoken_article_decomposition(self):
        decomposer = RuleBasedTaskDecomposer()
        actions = decomposer.decompose("open Notepad and type hello aura and save it as a Aura")

        assert len(actions) == 5
        assert actions[0].action_type == ActionType.LAUNCH_APPLICATION
        assert actions[0].target == "notepad"
        assert actions[1].action_type == ActionType.TYPE_TEXT
        assert actions[1].value == "hello aura"
        assert actions[2].action_type == ActionType.HOTKEY
        assert actions[3].action_type == ActionType.TYPE_TEXT
        assert actions[3].value == "Aura.txt"
        assert actions[4].action_type == ActionType.PRESS_KEY
        assert actions[4].verification["path"] == "Aura.txt"


# ==============================================================================
# 7. EXPLORER & TERMINAL GUI WINDOW VERIFICATION REGRESSIONS
# ==============================================================================

class TestExplorerAndTerminalVerificationRegressions:
    """Verify that Explorer desktop shell and AURA host shell are not treated as target GUI windows."""

    def test_explorer_shell_na_title_not_counted_as_folder_window(self):
        am = ApplicationManager()

        # Mock find_process_windows returning only the desktop shell (Window Title == 'N/A')
        with patch("app.automation.application_manager.find_process_windows") as mock_find:
            mock_find.return_value = [{"pid": 1234, "image_name": "explorer.exe", "window_title": "N/A"}]
            assert am.is_window_open("explorer") is False

            # When an actual folder window exists (e.g. "Documents")
            mock_find.return_value = [
                {"pid": 1234, "image_name": "explorer.exe", "window_title": "N/A"},
                {"pid": 5678, "image_name": "explorer.exe", "window_title": "Documents"},
            ]
            assert am.is_window_open("explorer") is True

    def test_terminal_host_pid_exclusion(self):
        from app.verification.application_verifier import ApplicationVerifier

        verifier = ApplicationVerifier()
        current_pid = os.getpid()

        # If only current host process or background pipe is running, verification must not falsely pass
        with patch("app.verification.application_verifier.find_process_windows") as mock_find:
            # 1. Host process with matching PID
            mock_find.return_value = [{"pid": current_pid, "image_name": "powershell.exe", "window_title": "PowerShell"}]
            assert verifier._find_running_process(["powershell.exe"]) is None

            # 2. Process with N/A window title
            mock_find.return_value = [{"pid": 99999, "image_name": "powershell.exe", "window_title": "N/A"}]
            assert verifier._find_running_process(["powershell.exe"]) is None

            # 3. Real distinct GUI console window
            mock_find.return_value = [{"pid": 99999, "image_name": "powershell.exe", "window_title": "Windows PowerShell"}]
            found = verifier._find_running_process(["powershell.exe"])
            assert found == "powershell.exe"


# ==============================================================================
# 8. DUPLICATE SPEECH OUTPUT PREVENTION REGRESSIONS
# ==============================================================================

class TestDuplicateSpeechPreventionRegressions:
    """Verify each logical assistant response is generated and emitted exactly once."""

    def test_greeting_emits_single_message(self, capsys):
        mock_voice = MagicMock()
        agent = Agent(voice_manager=mock_voice)

        agent.process_text("hello")

        # mock_voice.speak should be called exactly once
        assert mock_voice.speak.call_count == 1
        assert "Hello! I am AURA" in mock_voice.speak.call_args[0][0]

    def test_capabilities_query_emits_single_message(self, capsys):
        mock_voice = MagicMock()
        agent = Agent(voice_manager=mock_voice)

        agent.process_text("what can you do")

        # mock_voice.speak should be called exactly once
        assert mock_voice.speak.call_count == 1
        assert "I can help you" in mock_voice.speak.call_args[0][0]

