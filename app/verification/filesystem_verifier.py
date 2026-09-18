"""
app/verification/filesystem_verifier.py

State-based verification for filesystem actions.
Verifies that expected file and directory transitions actually occurred.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class FileSystemVerifier:
    """
    Verifies actual filesystem state before and after actions.
    """

    @staticmethod
    def verify_create(path: str | Path) -> tuple[bool, str]:
        """Verify that a created file or directory exists."""
        p = Path(path)
        if p.exists():
            return True, f"Target '{p.name}' was created successfully."
        return False, f"Expected created path '{path}' does not exist."

    @staticmethod
    def verify_delete(path: str | Path) -> tuple[bool, str]:
        """Verify that a deleted file or directory no longer exists."""
        p = Path(path)
        if not p.exists():
            return True, f"Target '{p.name}' was deleted successfully."
        return False, f"Expected deleted path '{path}' still exists on disk."

    @staticmethod
    def verify_move(source: str | Path, destination: str | Path) -> tuple[bool, str]:
        """Verify that source was removed and destination exists."""
        src = Path(source)
        dst = Path(destination)
        if not src.exists() and dst.exists():
            return True, f"Successfully moved '{src.name}' to '{dst.name}'."
        if src.exists():
            return False, f"Move failed: source '{source}' still exists."
        return False, f"Move failed: destination '{destination}' does not exist."

    @staticmethod
    def verify_copy(source: str | Path, destination: str | Path) -> tuple[bool, str]:
        """Verify that both source and destination exist."""
        src = Path(source)
        dst = Path(destination)
        if src.exists() and dst.exists():
            return True, f"Successfully copied '{src.name}' to '{dst.name}'."
        if not dst.exists():
            return False, f"Copy failed: destination '{destination}' does not exist."
        return False, f"Copy failed: source '{source}' does not exist."

    @staticmethod
    def verify_rename(old_path: str | Path, new_path: str | Path) -> tuple[bool, str]:
        """Verify that old path is gone and new path exists."""
        old_p = Path(old_path)
        new_p = Path(new_path)
        if not old_p.exists() and new_p.exists():
            return True, f"Successfully renamed '{old_p.name}' to '{new_p.name}'."
        if old_p.exists():
            return False, f"Rename failed: original path '{old_path}' still exists."
        return False, f"Rename failed: new path '{new_path}' does not exist."

    @staticmethod
    def verify_write(path: str | Path, expected_snippet: str | None = None) -> tuple[bool, str]:
        """Verify that file exists and optionally contains expected content snippet."""
        p = Path(path)
        if not p.exists():
            return False, f"Write failed: file '{path}' does not exist."
        if expected_snippet:
            content = p.read_text(encoding="utf-8", errors="replace")
            if expected_snippet not in content:
                return False, f"Write failed: expected snippet was not found in '{path}'."
        return True, f"Successfully wrote to '{p.name}'."
