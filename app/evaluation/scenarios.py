"""
app/evaluation/scenarios.py

Standardized benchmark scenario suite for AURA evaluation.
Covers Desktop, Browser, Filesystem, Perception, Agent Intelligence,
Content Intelligence, and Tutoring modes.
"""

from __future__ import annotations

from app.evaluation.models import BenchmarkCategory, BenchmarkScenario


def get_standard_scenarios() -> list[BenchmarkScenario]:
    """Return canonical suite of deterministic evaluation scenarios."""
    return [
        # ====================================================================
        # 1. DESKTOP AUTOMATION
        # ====================================================================
        BenchmarkScenario(
            scenario_id="SC-DSK-01",
            category=BenchmarkCategory.DESKTOP,
            user_command="Open Notepad and type Hello AURA.",
            description="Launch Notepad application and enter text.",
            expected_environment="desktop",
            expected_action_sequence=["LAUNCH_APP", "TYPE_TEXT"],
            expected_final_state={"app_running": "notepad.exe"},
        ),
        BenchmarkScenario(
            scenario_id="SC-DSK-02",
            category=BenchmarkCategory.DESKTOP,
            user_command="Open Calculator",
            description="Launch Calculator application.",
            expected_environment="desktop",
            expected_action_sequence=["LAUNCH_APP"],
            expected_final_state={"app_running": "calc.exe"},
        ),

        # ====================================================================
        # 2. BROWSER AUTOMATION
        # ====================================================================
        BenchmarkScenario(
            scenario_id="SC-BRW-01",
            category=BenchmarkCategory.BROWSER,
            user_command="Open Chrome and navigate to Google",
            description="Launch Chrome browser and navigate to URL.",
            expected_environment="browser",
            expected_action_sequence=["LAUNCH_APP", "NAVIGATE_URL"],
            expected_final_state={"url": "https://www.google.com"},
        ),
        BenchmarkScenario(
            scenario_id="SC-BRW-02",
            category=BenchmarkCategory.BROWSER,
            user_command="Read this webpage and summarize it",
            description="Extract and summarize readable content from active webpage.",
            expected_environment="browser",
            expected_action_sequence=["EXTRACT_PAGE_CONTENT", "SUMMARIZE_DOCUMENT"],
            expected_final_state={"content_extracted": True},
        ),

        # ====================================================================
        # 3. FILESYSTEM AUTOMATION
        # ====================================================================
        BenchmarkScenario(
            scenario_id="SC-FS-01",
            category=BenchmarkCategory.FILESYSTEM,
            user_command="Create a folder called AURA Demo in Documents",
            description="Safely create directory in user documents.",
            expected_environment="filesystem",
            expected_action_sequence=["CREATE_FOLDER"],
            expected_final_state={"dir_exists": True},
        ),
        BenchmarkScenario(
            scenario_id="SC-FS-02",
            category=BenchmarkCategory.FILESYSTEM,
            user_command="Find file quarterly_report.pdf",
            description="Locate file in standard directories.",
            expected_environment="filesystem",
            expected_action_sequence=["LOCATE_FILE"],
            expected_final_state={"file_found": True},
        ),

        # ====================================================================
        # 4. COMPUTER PERCEPTION & GROUNDING
        # ====================================================================
        BenchmarkScenario(
            scenario_id="SC-PRC-01",
            category=BenchmarkCategory.PERCEPTION,
            user_command="Click the Save button",
            description="Ground and click button using UIElement visual reasoning.",
            expected_environment="desktop",
            expected_action_sequence=["CLICK"],
            expected_final_state={"clicked": True},
        ),
        BenchmarkScenario(
            scenario_id="SC-PRC-02",
            category=BenchmarkCategory.PERCEPTION,
            user_command="Click the second Submit button",
            description="Ordinal and spatial visual target disambiguation.",
            expected_environment="desktop",
            expected_action_sequence=["CLICK"],
            expected_final_state={"ordinal_grounded": True},
        ),

        # ====================================================================
        # 5. AGENT INTELLIGENCE & RECOVERY
        # ====================================================================
        BenchmarkScenario(
            scenario_id="SC-AGT-01",
            category=BenchmarkCategory.AGENT,
            user_command="Open report.pdf, summarize it, and save the summary as a Word document",
            description="Multi-step DAG execution with contextual entity resolution ($report, $summary).",
            expected_environment="content",
            expected_action_sequence=["EXTRACT_DOCUMENT", "SUMMARIZE_DOCUMENT", "CREATE_DOCX"],
            expected_final_state={"file_created": "report_summary.docx"},
        ),
        BenchmarkScenario(
            scenario_id="SC-AGT-02",
            category=BenchmarkCategory.AGENT,
            user_command="Cancel task",
            description="Graceful cancellation of running actions and task graph.",
            expected_environment="system",
            expected_action_sequence=[],
            expected_final_state={"state": "CANCELLED"},
        ),

        # ====================================================================
        # 6. CONTENT INTELLIGENCE
        # ====================================================================
        BenchmarkScenario(
            scenario_id="SC-CNT-01",
            category=BenchmarkCategory.CONTENT,
            user_command="Summarize this PDF report.pdf",
            description="PDF extraction, structured parsing, and extractive summarization.",
            expected_environment="content",
            expected_action_sequence=["EXTRACT_DOCUMENT", "SUMMARIZE_DOCUMENT"],
            expected_final_state={"summary_generated": True},
        ),
        BenchmarkScenario(
            scenario_id="SC-CNT-02",
            category=BenchmarkCategory.CONTENT,
            user_command="Find the highest AQI value in this spreadsheet air_quality.xlsx",
            description="XLSX coordinate extraction, aggregation, and cell provenance.",
            expected_environment="content",
            expected_action_sequence=["ANALYZE_SHEET"],
            expected_final_state={"max_calculated": True},
        ),
        BenchmarkScenario(
            scenario_id="SC-CNT-03",
            category=BenchmarkCategory.CONTENT,
            user_command="Turn this report into a presentation",
            description="Document extraction and PowerPoint slide deck generation.",
            expected_environment="content",
            expected_action_sequence=["EXTRACT_DOCUMENT", "SUMMARIZE_DOCUMENT", "CREATE_PPTX"],
            expected_final_state={"file_created": "report_presentation.pptx"},
        ),

        # ====================================================================
        # 7. TUTORING WORKFLOW (SHOW_ME_HOW)
        # ====================================================================
        BenchmarkScenario(
            scenario_id="SC-TUT-01",
            category=BenchmarkCategory.TUTORING,
            user_command="Show me how to open Notepad",
            description="Interactive step-by-step tutoring with WAITING_FOR_USER and verification.",
            expected_environment="tutoring",
            expected_action_sequence=["SPEAK", "WAIT_FOR_USER", "VERIFY"],
            expected_mode="SHOW_ME_HOW",
            expected_final_state={"tutoring_verified": True},
        ),
    ]
