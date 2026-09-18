"""
Tests for FileSystemVerifier.
"""

from __future__ import annotations

import os
from pathlib import Path
import pytest

from app.verification.filesystem_verifier import FileSystemVerifier


class TestFileSystemVerifier:
    def test_verify_create(self, tmp_path):
        f = tmp_path / "created.txt"
        
        ok, msg = FileSystemVerifier.verify_create(f)
        assert ok is False

        f.write_text("hello", encoding="utf-8")
        ok, msg = FileSystemVerifier.verify_create(f)
        assert ok is True

    def test_verify_delete(self, tmp_path):
        f = tmp_path / "to_delete.txt"
        f.write_text("bye", encoding="utf-8")

        ok, msg = FileSystemVerifier.verify_delete(f)
        assert ok is False

        f.unlink()
        ok, msg = FileSystemVerifier.verify_delete(f)
        assert ok is True

    def test_verify_move(self, tmp_path):
        src = tmp_path / "src.txt"
        dst = tmp_path / "dst.txt"
        src.write_text("move me", encoding="utf-8")

        # Before move
        ok, _ = FileSystemVerifier.verify_move(src, dst)
        assert ok is False

        # Perform move
        src.rename(dst)
        ok, msg = FileSystemVerifier.verify_move(src, dst)
        assert ok is True

    def test_verify_copy(self, tmp_path):
        src = tmp_path / "original.txt"
        dst = tmp_path / "copied.txt"
        src.write_text("content", encoding="utf-8")

        ok, _ = FileSystemVerifier.verify_copy(src, dst)
        assert ok is False

        dst.write_text("content", encoding="utf-8")
        ok, msg = FileSystemVerifier.verify_copy(src, dst)
        assert ok is True

    def test_verify_rename(self, tmp_path):
        old_f = tmp_path / "old.txt"
        new_f = tmp_path / "new.txt"
        old_f.write_text("test", encoding="utf-8")

        ok, _ = FileSystemVerifier.verify_rename(old_f, new_f)
        assert ok is False

        old_f.rename(new_f)
        ok, msg = FileSystemVerifier.verify_rename(old_f, new_f)
        assert ok is True

    def test_verify_write(self, tmp_path):
        f = tmp_path / "written.txt"
        ok, _ = FileSystemVerifier.verify_write(f)
        assert ok is False

        f.write_text("The quick brown fox jumps over the lazy dog", encoding="utf-8")
        ok, msg = FileSystemVerifier.verify_write(f, expected_snippet="brown fox")
        assert ok is True

        ok, msg = FileSystemVerifier.verify_write(f, expected_snippet="missing text xyz")
        assert ok is False
