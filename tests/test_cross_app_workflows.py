"""
Tests for Cross-Application Workflows and Multi-Step Task Decomposition with Dependencies.
"""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from app.config.constants import AssistantMode
from app.intelligence.action import Action, ActionType
from app.intelligence.planner import Planner
from app.intelligence.task_decomposer import RuleBasedTaskDecomposer


class TestCrossAppWorkflows:
    def setup_method(self):
        self.decomposer = RuleBasedTaskDecomposer()
        self.planner = Planner(decomposer=self.decomposer)

    def test_workflow_chrome_search(self):
        # Workflow: "open chrome and search for AURA"
        actions = self.decomposer.decompose("open chrome and search for AURA")
        assert len(actions) == 2
        
        act1, act2 = actions[0], actions[1]
        assert act1.action_type == ActionType.LAUNCH_APPLICATION
        assert act1.target == "chrome"
        assert act1.action_id == "act_open_chrome"

        assert act2.action_type == ActionType.OPEN_URL
        assert "search?q=aura" in act2.target.lower()
        assert "act_open_chrome" in act2.dependencies

    def test_workflow_chrome_search_and_save_to_file(self):
        # Workflow: "open chrome, search for AI Agents, and save to a text file"
        actions = self.decomposer.decompose("open chrome, search for AI Agents, and save to a text file")
        assert len(actions) == 3

        act1_browser = actions[0]
        act2_extract = actions[1]
        act3_save = actions[2]

        assert act1_browser.action_type == ActionType.OPEN_URL
        assert "search?q=ai agents" in act1_browser.target.lower()

        assert act2_extract.action_type == ActionType.EXTRACT_PAGE_CONTENT
        assert act1_browser.action_id in act2_extract.dependencies

        assert act3_save.action_type == ActionType.CREATE_FILE
        assert act2_extract.action_id in act3_save.dependencies

    def test_workflow_create_folder_and_move_file(self):
        # Workflow: "create a folder called AURA in Downloads and move report.docx into it"
        actions = self.decomposer.decompose("create a folder called AURA in Downloads and move report.docx into it")
        assert len(actions) == 2

        act_folder = actions[0]
        act_move = actions[1]

        assert act_folder.action_type == ActionType.CREATE_FOLDER
        assert act_folder.target == "AURA"

        assert act_move.action_type == ActionType.MOVE_FILE
        assert act_move.target == "report.docx"
        assert act_move.value == "AURA"
        assert act_folder.action_id in act_move.dependencies

    def test_workflow_filesystem_single_actions(self):
        # Create folder
        actions_mkdir = self.decomposer.decompose("create folder Projects")
        assert len(actions_mkdir) == 1
        assert actions_mkdir[0].action_type == ActionType.CREATE_FOLDER

        # Rename
        actions_ren = self.decomposer.decompose("rename draft.txt to final.txt")
        assert len(actions_ren) == 1
        assert actions_ren[0].action_type == ActionType.RENAME_FILE
        assert actions_ren[0].target == "draft.txt"
        assert actions_ren[0].value == "final.txt"

        # Delete
        actions_del = self.decomposer.decompose("delete old_log.txt")
        assert len(actions_del) == 1
        assert actions_del[0].action_type == ActionType.DELETE_FILE
        assert actions_del[0].target == "old_log.txt"
