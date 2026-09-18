"""
Comprehensive unit tests for the AURA reliability refactor:
1. Canonical UIElement conversion & TextElement handling (perception type mismatch fix).
2. Chrome & Edge application decomposition (LAUNCH_APPLICATION).
3. SPEAK action routing through communication channel (bypassing ActionExecutor).
4. Spatial reasoning & relational target queries ('beside', ordinals, directional).
5. TutoringController speech deduplication and single-character OCR noise rejection.
6. Startup greeting lifecycle.
"""

from unittest.mock import MagicMock, patch
import pytest

from app.intelligence.action import Action, ActionType
from app.core.agent import Agent
from app.intelligence.intent import Intent
from app.intelligence.planner import Planner
from app.intelligence.task_decomposer import RuleBasedTaskDecomposer
from app.perception.ocr import TextElement
from app.perception.ui_element import UIElement, as_ui_element, to_ui_elements
from app.perception.target_query import parse_target_query, TargetQuery
from app.perception.spatial_reasoner import SpatialReasoner
from app.perception.grounding import UIGrounder
from app.tutoring.tutoring_controller import TutoringController
from app.tutoring.instruction import TutoringInstruction
from app.core.observation import ScreenObservation
from app.core.observation_diff import ObservationDiff, ObservationDiffer


# ---------------------------------------------------------------------------
# 1. Perception Type Mismatch Fix: to_ui_elements & as_ui_element
# ---------------------------------------------------------------------------

class TestUIElementConversion:

    def test_text_element_converted_to_ui_element_with_id(self):
        """TextElement lacks element_id; converter must add unique element_id."""
        text_elem = TextElement(
            text="Save",
            x=100,
            y=50,
            width=80,
            height=30,
            confidence=0.98,
        )
        assert not hasattr(text_elem, "element_id") or getattr(text_elem, "element_id", None) is None

        ui_elem = as_ui_element(text_elem, index=1)
        assert isinstance(ui_elem, UIElement)
        assert ui_elem.element_id == "ocr-1"
        assert ui_elem.text == "Save"
        assert ui_elem.x == 100
        assert ui_elem.y == 50
        assert ui_elem.width == 80
        assert ui_elem.height == 30
        assert ui_elem.confidence == 0.98

    def test_to_ui_elements_batch_conversion(self):
        """Batch converter handles mixed lists and assigns sequential IDs."""
        raw_elements = [
            TextElement(text="File", x=10, y=10, width=40, height=20, confidence=0.9),
            TextElement(text="Edit", x=60, y=10, width=40, height=20, confidence=0.95),
        ]
        converted = to_ui_elements(raw_elements)
        assert len(converted) == 2
        assert converted[0].element_id == "ocr-0"
        assert converted[0].text == "File"
        assert converted[1].element_id == "ocr-1"
        assert converted[1].text == "Edit"

    def test_to_ui_elements_preserves_existing_ui_elements(self):
        """Already canonical UIElement instances should be preserved with their IDs."""
        original = UIElement(
            element_id="btn_submit",
            element_type="button",
            text="Submit",
            x=200, y=300, width=100, height=40,
        )
        converted = to_ui_elements([original])
        assert len(converted) == 1
        assert converted[0].element_id == "btn_submit"
        assert converted[0].text == "Submit"

    def test_to_ui_elements_empty_or_none(self):
        assert to_ui_elements(None) == []
        assert to_ui_elements([]) == []


# ---------------------------------------------------------------------------
# 2. Chrome & Edge Decomposition Fix
# ---------------------------------------------------------------------------

class TestApplicationDecomposition:

    def test_open_chrome_decomposes_to_launch_application(self):
        """'open Chrome' must produce LAUNCH_APPLICATION, NOT unsupported SPEAK."""
        decomposer = RuleBasedTaskDecomposer()
        actions = decomposer.decompose("open Chrome")

        assert len(actions) == 1
        action = actions[0]
        assert action.action_type == ActionType.LAUNCH_APPLICATION
        assert action.target == "chrome"
        assert "chrome.exe" in (
            action.verification.get("processes", [])
            or [action.verification.get("process", "")]
        )

    def test_open_google_chrome_decomposes_correctly(self):
        decomposer = RuleBasedTaskDecomposer()
        actions = decomposer.decompose("launch google chrome")

        assert len(actions) == 1
        assert actions[0].action_type == ActionType.LAUNCH_APPLICATION
        assert actions[0].target == "chrome"

    def test_open_edge_decomposes_to_launch_application(self):
        decomposer = RuleBasedTaskDecomposer()
        actions = decomposer.decompose("open edge")

        assert len(actions) == 1
        action = actions[0]
        assert action.action_type == ActionType.LAUNCH_APPLICATION
        assert action.target == "msedge"
        assert "msedge.exe" in (
            action.verification.get("processes", [])
            or [action.verification.get("process", "")]
        )


# ---------------------------------------------------------------------------
# 3. SPEAK Action Execution Bug Fix: Bypassing ActionExecutor
# ---------------------------------------------------------------------------

class TestSpeakActionRouting:

    def test_speak_action_bypasses_action_executor(self):
        """
        When the planner produces a SPEAK action, Agent must speak it
        via voice_manager and NEVER send it to ActionExecutor.
        """
        mock_voice = MagicMock()
        mock_executor = MagicMock()

        agent = Agent(
            voice_manager=mock_voice,
            action_executor=mock_executor,
        )

        speak_action = Action(
            action_type=ActionType.SPEAK,
            value="Hello, this is a test speech.",
            description="Speak message",
        )

        result = agent._execute_action(speak_action)

        # ActionExecutor must NOT be called for SPEAK
        mock_executor.execute.assert_not_called()
        # VoiceManager must speak the message
        mock_voice.speak.assert_called_once_with("Hello, this is a test speech.")
        assert result == speak_action

    def test_verify_action_ignores_speak(self):
        """_verify_action should gracefully return without error on SPEAK."""
        mock_verifier = MagicMock()
        agent = Agent(application_verifier=mock_verifier)

        speak_action = Action(
            action_type=ActionType.SPEAK,
            value="Speech",
        )
        # Should not raise RuntimeError or call verifier
        agent._verify_action(speak_action)
        mock_verifier.verify.assert_not_called()


# ---------------------------------------------------------------------------
# 4. Spatial Reasoning & Relational Queries
# ---------------------------------------------------------------------------

class TestSpatialReasoningAndQueries:

    def test_parse_target_query_beside(self):
        query = parse_target_query("the button beside search")
        assert query.element_type == "button" or query.text == "button"
        assert query.relation == "beside"
        assert query.reference == "search"

    def test_parse_target_query_ordinal(self):
        query = parse_target_query("the second tab")
        assert query.ordinal == 2
        assert query.text == "tab" or query.element_type == "tab" or query.group == "tab"

    def test_resolve_beside_spatial_reasoner(self):
        reasoner = SpatialReasoner()
        anchor = UIElement(
            element_id="search_box",
            element_type="input",
            text="Search",
            x=200, y=100, width=150, height=30,
        )
        beside_btn = UIElement(
            element_id="go_btn",
            element_type="button",
            text="Go",
            x=360, y=100, width=40, height=30,  # 10px right of anchor, same row
        )
        far_btn = UIElement(
            element_id="far_btn",
            element_type="button",
            text="Far",
            x=200, y=600, width=40, height=30,  # vertically far
        )

        candidates = [beside_btn, far_btn]
        result = reasoner.resolve_beside(candidates, anchor)
        assert result.found is True
        assert result.element is beside_btn


# ---------------------------------------------------------------------------
# 5. Speech Deduplication & False-Positive Verification Rejection
# ---------------------------------------------------------------------------

class TestTutoringControllerReliability:

    def test_speak_does_not_duplicate_print(self, capsys):
        """
        When TTS or VoiceManager is active, TutoringController._speak
        must delegate to it and NOT independently print 'AURA: ...'.
        """
        mock_voice = MagicMock()
        ctrl = TutoringController(
            observer=MagicMock(),
            tutoring_engine=MagicMock(),
            voice_manager=mock_voice,
        )

        ctrl._speak("Step 1: Open Start menu")
        mock_voice.speak.assert_called_once_with("Step 1: Open Start menu")

        captured = capsys.readouterr()
        # Should not have printed duplicate AURA prefix in stdout from _speak
        assert captured.out == ""

    def test_verify_type_text_rejects_single_char_substring_noise(self):
        """
        Typing 'notepad' must NOT be verified because a 1-character token
        like 'e' appeared in diff.added_text.
        """
        ctrl = TutoringController(
            observer=MagicMock(),
            tutoring_engine=MagicMock(),
        )

        diff = MagicMock()
        diff.added_text = ["e"]  # single noisy OCR token

        before = ScreenObservation(screen_text="")
        after = ScreenObservation(screen_text="e")

        verified = ctrl._verify_type_text("notepad", diff, before, after)
        assert not verified, "Single-letter noise 'e' must not verify 'notepad'!"

    def test_verify_type_text_accepts_actual_typed_text(self):
        ctrl = TutoringController(
            observer=MagicMock(),
            tutoring_engine=MagicMock(),
        )

        diff = MagicMock()
        diff.added_text = ["notepad"]

        before = ScreenObservation(screen_text="")
        after = ScreenObservation(screen_text="notepad")

        verified = ctrl._verify_type_text("notepad", diff, before, after)
        assert verified

    def test_verify_press_key_win_rejects_clock_noise(self):
        """
        Pressing Win key must reject a single added token (e.g. clock update).
        """
        ctrl = TutoringController(
            observer=MagicMock(),
            tutoring_engine=MagicMock(),
        )

        diff = MagicMock()
        diff.process_change = False
        diff.window_title_changed = False
        diff.added_elements = [MagicMock()]  # only 1 element
        diff.added_text = ["12:00"]          # only clock token

        completion = {"screen_changed": True}
        expected = {}
        parameters = {"key": "win"}

        verified = ctrl._verify_press_key(completion, expected, diff, parameters)
        assert not verified, "Win key verification must reject single-token clock noise"

    def test_verify_press_key_win_accepts_start_keywords(self):
        """
        Pressing Win key accepts Start menu / Search keywords.
        """
        ctrl = TutoringController(
            observer=MagicMock(),
            tutoring_engine=MagicMock(),
        )

        diff = MagicMock()
        diff.process_change = False
        diff.window_title_changed = False
        diff.added_elements = []
        diff.added_text = ["Type here to search"]

        completion = {"screen_changed": True}
        expected = {}
        parameters = {"key": "win"}

        verified = ctrl._verify_press_key(completion, expected, diff, parameters)
        assert verified
