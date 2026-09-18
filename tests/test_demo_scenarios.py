"""
tests/test_demo_scenarios.py

Automated verification of the 10 canonical demonstration scenarios for AURA Semester 1.
"""

from unittest.mock import MagicMock

from app.config.constants import AssistantMode, AssistantState
from app.core.agent import Agent
from app.core.failure import FailureClassifier, FailureInfo, FailureType
from app.core.observation import ScreenObservation
from app.core.recovery_engine import RecoveryEngine
from app.intelligence.action import Action, ActionType
from app.intelligence.intent_parser import IntentParser
from app.intelligence.planner import Planner
from app.intelligence.task_context import TaskContext
from app.intelligence.task_decomposer import TaskDecomposer
from app.tutoring.tutoring_controller import TutoringController, TutoringState


class TestDemoScenarios:
    def setup_method(self):
        self.intent_parser = IntentParser()
        self.decomposer = TaskDecomposer()
        self.planner = Planner()

    # Demo 1: Desktop
    def test_demo_1_desktop_open_notepad_and_type(self):
        command = "Open Notepad and type Hello AURA."
        actions = self.decomposer.decompose(command)
        assert len(actions) >= 2
        assert actions[0].action_type == ActionType.LAUNCH_APPLICATION
        assert "notepad" in actions[0].target.lower()
        assert actions[1].action_type == ActionType.TYPE_TEXT
        assert "hello aura" in actions[1].value.lower()

    # Demo 2: Browser
    def test_demo_2_browser_open_chrome_and_navigate(self):
        command = "Open Chrome and go to Google."
        actions = self.decomposer.decompose(command)
        assert len(actions) >= 2
        assert actions[0].action_type == ActionType.LAUNCH_APPLICATION
        assert "chrome" in actions[0].target.lower()
        assert actions[1].action_type == ActionType.NAVIGATE_URL
        assert "google.com" in actions[1].target.lower()

    # Demo 3: Filesystem
    def test_demo_3_filesystem_create_folder(self):
        command = "Create a folder called AURA Demo in Documents."
        actions = self.decomposer.decompose(command)
        assert len(actions) >= 1
        assert actions[0].action_type == ActionType.CREATE_FOLDER
        assert "AURA Demo" in actions[0].target or "aura demo" in actions[0].target.lower()

    # Demo 4: Context
    def test_demo_4_context_summarize_and_save_word(self):
        command = "Open the report, summarize it, and save the summary as a Word document."
        actions = self.decomposer.decompose(command)
        assert len(actions) == 3
        assert actions[0].action_type == ActionType.EXTRACT_DOCUMENT
        assert actions[1].action_type == ActionType.SUMMARIZE_DOCUMENT
        assert actions[2].action_type == ActionType.CREATE_DOCX

    # Demo 5: Spreadsheet
    def test_demo_5_spreadsheet_find_highest_aqi(self):
        command = "Find the highest AQI value in this spreadsheet air_quality.xlsx"
        actions = self.decomposer.decompose(command)
        assert len(actions) == 1
        assert actions[0].action_type == ActionType.ANALYZE_SHEET
        assert "air_quality.xlsx" in actions[0].target

    # Demo 6: Presentation
    def test_demo_6_presentation_turn_report_into_presentation(self):
        command = "Turn this report into a presentation."
        actions = self.decomposer.decompose(command)
        assert len(actions) == 3
        assert actions[0].action_type == ActionType.EXTRACT_DOCUMENT
        assert actions[1].action_type == ActionType.SUMMARIZE_DOCUMENT
        assert actions[2].action_type == ActionType.CREATE_PPTX

    # Demo 7: Web Content
    def test_demo_7_web_read_webpage_and_summarize(self):
        command = "Read this webpage and summarize it."
        actions = self.decomposer.decompose(command)
        assert len(actions) == 2
        assert actions[0].action_type == ActionType.EXTRACT_PAGE_CONTENT
        assert actions[1].action_type == ActionType.SUMMARIZE_DOCUMENT

    # Demo 8: Recovery
    def test_demo_8_recovery_loop(self):
        action = Action(action_type=ActionType.CLICK, target="Save")
        failure = FailureInfo(
            action=action,
            failure_type=FailureType.TARGET_NOT_FOUND,
            error="Target 'Save' not found on screen.",
            attempt=1,
        )

        recovery_engine = RecoveryEngine()
        plan = recovery_engine.plan_recovery(failure=failure)
        assert plan.strategy is not None
        assert plan.can_continue is True

    # Demo 9: Tutoring
    def test_demo_9_tutoring_workflow(self):
        mock_vm = MagicMock()
        mock_observer = MagicMock()
        mock_observer.observe.return_value = ScreenObservation(screen_text="Notepad opened", processes=["notepad.exe"])

        engine = MagicMock()
        engine.describe_target.return_value = "Notepad"
        engine.screenshot_capture = None
        engine.ocr = None

        controller = TutoringController(
            voice_manager=mock_vm,
            observer=mock_observer,
            tutoring_engine=engine,
            poll_interval=0.0,
            step_timeout=0.1,
        )

        intent = self.intent_parser.parse("Show me how to open Notepad")
        task = self.planner.create_task(intent)
        assert task.mode == AssistantMode.SHOW_ME_HOW

        # Controller runs tutoring flow
        res = controller.run(task)
        assert res is not None

    # Demo 10: Cancellation
    def test_demo_10_cancellation(self):
        mock_vm = MagicMock()
        agent = Agent(voice_manager=mock_vm)

        agent.process_text("cancel")
        assert agent.state.current_state == AssistantState.IDLE
        mock_vm.speak.assert_called_with("Task cancelled.")
