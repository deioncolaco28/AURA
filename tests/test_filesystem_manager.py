"""
Tests for FileSystemManager.
"""

from __future__ import annotations

import os
from pathlib import Path
import pytest

from app.automation.filesystem_manager import FileSystemManager, FileCandidate, FileAmbiguityResult
from app.config.constants import RiskLevel


class TestFileSystemManager:
    def setup_method(self):
        self.fm = FileSystemManager()

    def test_create_read_write_file(self, tmp_path):
        fm = FileSystemManager(base_directory=tmp_path)

        created_path = fm.create_file("test.txt", "Initial content")
        assert os.path.exists(created_path)
        assert fm.read_file("test.txt") == "Initial content"

        # Overwrite
        fm.write_file("test.txt", "Updated content", overwrite=True)
        assert fm.read_file("test.txt") == "Updated content"

        # Overwrite=False should raise FileExistsError
        with pytest.raises(FileExistsError):
            fm.write_file("test.txt", "New content", overwrite=False)

    def test_create_and_list_folder(self, tmp_path):
        fm = FileSystemManager(base_directory=tmp_path)

        fm.create_folder("subfolder")
        fm.create_file("subfolder/file1.txt", "Data 1")
        fm.create_file("subfolder/file2.txt", "Data 2")

        listing = fm.list_directory("subfolder")
        assert len(listing) == 2
        assert any("file1.txt" in f for f in listing)
        assert any("file2.txt" in f for f in listing)

    def test_copy_move_rename_delete(self, tmp_path):
        fm = FileSystemManager(base_directory=tmp_path)

        fm.create_file("doc.txt", "Sample")
        
        # Copy
        fm.copy_path("doc.txt", "doc_copy.txt")
        assert os.path.exists(tmp_path / "doc.txt")
        assert os.path.exists(tmp_path / "doc_copy.txt")

        # Rename
        fm.rename_path("doc_copy.txt", "doc_renamed.txt")
        assert not os.path.exists(tmp_path / "doc_copy.txt")
        assert os.path.exists(tmp_path / "doc_renamed.txt")

        # Move
        fm.create_folder("archive")
        fm.move_path("doc_renamed.txt", "archive/doc_moved.txt")
        assert not os.path.exists(tmp_path / "doc_renamed.txt")
        assert os.path.exists(tmp_path / "archive/doc_moved.txt")

        # Delete
        fm.delete_path("archive/doc_moved.txt")
        assert not os.path.exists(tmp_path / "archive/doc_moved.txt")

    def test_compress_and_extract(self, tmp_path):
        fm = FileSystemManager(base_directory=tmp_path)

        fm.create_file("data1.txt", "Hello 1")
        fm.create_file("data2.txt", "Hello 2")

        zip_path = fm.compress_archive(["data1.txt", "data2.txt"], "bundle.zip")
        assert os.path.exists(zip_path)

        extracted_dir = fm.extract_archive("bundle.zip", "extracted_output")
        assert os.path.exists(tmp_path / "extracted_output/data1.txt")
        assert os.path.exists(tmp_path / "extracted_output/data2.txt")

    def test_search_files_ranking_and_ambiguity(self, tmp_path):
        fm = FileSystemManager(base_directory=tmp_path)

        fm.create_file("project_report.docx", "report content")
        fm.create_file("annual_project_report.docx", "annual report")
        fm.create_file("random_notes.txt", "notes")

        candidates = fm.search_files("project_report", directory=tmp_path)
        assert len(candidates) >= 2
        # Exact match should have score 1.0 and be top
        assert candidates[0].filename == "project_report.docx"
        assert candidates[0].score == 1.0

        ambiguity: FileAmbiguityResult = fm.check_ambiguity("project_report", candidates)
        assert isinstance(ambiguity.is_ambiguous, bool)

    def test_risk_classification(self):
        assert FileSystemManager.get_operation_risk("read") == RiskLevel.LOW
        assert FileSystemManager.get_operation_risk("list") == RiskLevel.LOW
        assert FileSystemManager.get_operation_risk("create") == RiskLevel.MEDIUM
        assert FileSystemManager.get_operation_risk("move") == RiskLevel.MEDIUM
        assert FileSystemManager.get_operation_risk("delete") == RiskLevel.HIGH
