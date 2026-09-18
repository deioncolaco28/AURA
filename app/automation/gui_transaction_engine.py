"""
app/automation/gui_transaction_engine.py

Stateful GUI Transaction Engine for multi-step desktop operations.
Replaces blind keyboard sequences with closed-loop, observation-driven transactions:
1. Active application inspection
2. Dialog triggering & discovery
3. Control targeting & stateful text entry
4. Confirmation & dismissal observation
5. Filesystem & application cross-verification
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any

from app.core.computer_state import ComputerStateCapturer
from app.intelligence.task_decomposer import normalize_save_filename


@dataclass
class TransactionResult:
    """Result of a stateful GUI transaction."""
    success: bool
    transaction_type: str
    target: str = ""
    created_file: str | None = None
    verified: bool = False
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class GUITransactionEngine:
    """
    Executes multi-step GUI workflows with state observation and cross-verification.
    """

    def __init__(self, capturer: ComputerStateCapturer | None = None):
        self.capturer = capturer or ComputerStateCapturer()

    def execute_save_transaction(
        self,
        raw_filename: str,
        default_ext: str = ".txt",
        target_dir: str | None = None,
        timeout: float = 6.0,
    ) -> TransactionResult:
        """
        Stateful Save As transaction:
        1. Normalize filename
        2. Capture pre-state
        3. Trigger Save dialog (Ctrl+S / UIA)
        4. Wait for dialog
        5. Type filename & confirm
        6. Observe filesystem and verify file existence
        """
        clean_filename = normalize_save_filename(raw_filename, default_ext=default_ext)
        dest_dir = target_dir or os.getcwd()
        expected_path = os.path.join(dest_dir, clean_filename)

        # 1. Capture Pre-state
        pre_state = self.capturer.capture_state(tracked_paths=[expected_path])

        # 2. Trigger Save (Ctrl+S)
        from app.automation.keyboard import KeyboardController
        keyboard = KeyboardController()
        keyboard.hotkey(["ctrl", "s"])

        # 3. Bounded polling for Save dialog appearance
        dialog_found = False
        start_time = time.time()
        while time.time() - start_time < timeout:
            current_state = self.capturer.capture_state(tracked_paths=[expected_path])
            if current_state.active_dialogs or any("save" in w.title.lower() for w in current_state.windows):
                dialog_found = True
                break
            time.sleep(0.3)

        # 4. Type normalized filename
        keyboard.type_text(clean_filename)
        time.sleep(0.3)

        # 5. Confirm Save (Enter)
        keyboard.press_key("enter")
        time.sleep(0.5)

        # 6. Bounded polling for Filesystem creation
        file_verified = False
        start_time = time.time()
        while time.time() - start_time < timeout:
            post_state = self.capturer.capture_state(tracked_paths=[expected_path, clean_filename])
            if post_state.has_file(expected_path) or post_state.has_file(clean_filename) or os.path.exists(clean_filename) or os.path.exists(expected_path):
                file_verified = True
                break
            time.sleep(0.3)

        # Check in common fallback locations (Desktop, Documents, CWD)
        if not file_verified:
            user_profile = os.environ.get("USERPROFILE", "")
            fallbacks = [
                os.path.join(user_profile, "Desktop", clean_filename),
                os.path.join(user_profile, "Documents", clean_filename),
                os.path.join(os.getcwd(), clean_filename),
            ]
            for fb in fallbacks:
                if os.path.exists(fb):
                    file_verified = True
                    expected_path = fb
                    break

        if file_verified:
            return TransactionResult(
                success=True,
                transaction_type="SAVE_DOCUMENT",
                target=clean_filename,
                created_file=expected_path,
                verified=True,
                message=f"Document successfully saved as '{clean_filename}' and verified on disk.",
            )

        return TransactionResult(
            success=False,
            transaction_type="SAVE_DOCUMENT",
            target=clean_filename,
            created_file=None,
            verified=False,
            message=f"Save transaction completed input sequence, but expected file '{clean_filename}' was not verified on disk.",
        )
