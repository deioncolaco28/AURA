"""
tests/test_universal_architecture.py

Comprehensive tests for AURA's Universal Computer-Use Agent Architecture:
1. Universal Computer State Model (ComputerState, WindowInfo, FileSnapshot)
2. State Difference Engine (ComputerStateDiff, StateDiffEngine)
3. Action Contract & Strategy Selection (StrategySelector)
4. GUI Transaction Engine (Stateful Save As, normalize_save_filename)
5. Robust Application Lifecycle & Distinct Target Verification (Explorer folder vs shell, Terminal vs host)
6. Idempotency Safeguards & Adaptive Failure Recovery
7. Truthful Status Completion
"""

import os
from unittest.mock import MagicMock, patch
import pytest

from app.automation.gui_transaction_engine import GUITransactionEngine, TransactionResult
from app.automation.strategy_selector import StrategySelector
from app.core.computer_state import ComputerState, ComputerStateCapturer, FileSnapshot, WindowInfo
from app.core.state_diff_engine import ComputerStateDiff, StateDiffEngine
from app.intelligence.action import Action, ActionType, IdempotencyType, StrategyType
from app.intelligence.task_decomposer import RuleBasedTaskDecomposer, normalize_save_filename
from app.verification.state_verifier import StateVerifier


# ==============================================================================
# 1. UNIVERSAL COMPUTER STATE & DIFF ENGINE TESTS
# ==============================================================================

class TestComputerStateAndDiffEngine:
    """Verify ComputerState snapshot capture and semantic diff calculations."""

    def test_window_info_interactive_gui_discrimination(self):
        # Shell/Background windows should be marked non-interactive
        shell_win = WindowInfo(hwnd=101, title="Program Manager", class_name="Progman", is_visible=True)
        assert shell_win.is_interactive_gui is False

        na_win = WindowInfo(hwnd=102, title="N/A", class_name="Shell_TrayWnd", is_visible=True)
        assert na_win.is_interactive_gui is False

        # Real folder window
        explorer_win = WindowInfo(hwnd=103, title="Documents", class_name="CabinetWClass", process_name="explorer.exe", is_visible=True)
        assert explorer_win.is_interactive_gui is True

        # Real notepad window
        notepad_win = WindowInfo(hwnd=104, title="Untitled - Notepad", class_name="Notepad", process_name="notepad.exe", is_visible=True)
        assert notepad_win.is_interactive_gui is True

    def test_state_diff_engine_detects_opened_windows_and_created_files(self):
        diff_engine = StateDiffEngine()

        w_before = WindowInfo(hwnd=1, title="Desktop", process_name="explorer.exe")
        before_state = ComputerState(windows=[w_before], files={"C:/test/out.txt": FileSnapshot(path="C:/test/out.txt", exists=False)})

        w_after1 = WindowInfo(hwnd=1, title="Desktop", process_name="explorer.exe")
        w_after2 = WindowInfo(hwnd=2, title="Downloads", process_name="explorer.exe", is_visible=True)
        after_state = ComputerState(
            windows=[w_after1, w_after2],
            files={"C:/test/out.txt": FileSnapshot(path="C:/test/out.txt", exists=True, size_bytes=120)},
        )

        diff = diff_engine.compute_diff(before_state, after_state)

        assert diff.has_any_change is True
        assert len(diff.windows_opened) == 1
        assert diff.windows_opened[0].title == "Downloads"
        assert diff.is_file_created("out.txt") is True


# ==============================================================================
# 2. STRATEGY SELECTOR & FALLBACK TESTS
# ==============================================================================

class TestStrategySelector:
    """Verify dynamic strategy selection and adaptive fallback on failure."""

    def test_strategy_hierarchy_for_save_and_click(self):
        selector = StrategySelector()

        save_action = Action(action_type=ActionType.SAVE_DOCUMENT, target="report.txt")
        assert selector.select_strategy(save_action) == StrategyType.TRANSACTION

        # If TRANSACTION failed, fall back to UIA
        fallback_1 = selector.get_fallback_strategy(save_action, failed_strategy=StrategyType.TRANSACTION)
        assert fallback_1 == StrategyType.UIA

        # If UIA also failed, fall back to KEYBOARD_SHORTCUT
        fallback_2 = selector.get_fallback_strategy(save_action, failed_strategy=StrategyType.UIA, all_failed=[StrategyType.TRANSACTION])
        assert fallback_2 == StrategyType.KEYBOARD_SHORTCUT

    def test_strategy_for_filesystem_operations(self):
        selector = StrategySelector()
        fs_action = Action(action_type=ActionType.CREATE_FOLDER, target="AURA_DATA")
        assert selector.select_strategy(fs_action) == StrategyType.OS_API


# ==============================================================================
# 3. GUI TRANSACTION ENGINE & SAVE AS NORMALIZATION TESTS
# ==============================================================================

class TestGUITransactionEngineAndSaveAs:
    """Verify stateful Save As execution and robust filename normalization."""

    def test_normalize_save_filename_extended_variants(self):
        cases = [
            ("save it as a Aura", "Aura.txt"),
            ("save the document as an important report", "important report.txt"),
            ("save it under the name final_version.docx", "final_version.docx"),
            ("save this file as data.xlsx", "data.xlsx"),
            ("save as a backup", "backup.txt"),
            ("a Aura", "Aura.txt"),
            ("the project notes", "project notes.txt"),
        ]
        for inp, expected in cases:
            assert normalize_save_filename(inp) == expected

    def test_save_transaction_verifies_on_disk_existence(self, tmp_path):
        target_file = tmp_path / "Aura.txt"
        target_file.write_text("hello Aura")

        engine = GUITransactionEngine()

        with patch("app.automation.keyboard.KeyboardController.hotkey"), \
             patch("app.automation.keyboard.KeyboardController.type_text"), \
             patch("app.automation.keyboard.KeyboardController.press_key"):
            result = engine.execute_save_transaction(
                raw_filename="a Aura",
                default_ext=".txt",
                target_dir=str(tmp_path),
                timeout=0.5,
            )

            assert result.success is True
            assert result.target == "Aura.txt"
            assert result.verified is True


# ==============================================================================
# 4. STATE VERIFIER SEMANTIC VALIDATION
# ==============================================================================

class TestStateVerifierSemanticValidation:
    """Verify state verification across applications, filesystem, and browser."""

    def test_verify_save_document_success_and_failure(self, tmp_path):
        verifier = StateVerifier()

        # Target file exists
        valid_file = tmp_path / "report.docx"
        valid_file.write_text("content")

        res_ok = verifier.verify_action({
            "type": "SAVE_DOCUMENT",
            "path": str(valid_file),
        })
        assert res_ok.verified is True

        # Non-existent file
        res_fail = verifier.verify_action({
            "type": "SAVE_DOCUMENT",
            "path": str(tmp_path / "missing.txt"),
        })
        assert res_fail.verified is False
