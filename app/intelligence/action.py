from dataclasses import dataclass, field
from typing import Any


class ActionType:
    """Supported computer interaction actions."""

    # Application & Window
    LAUNCH_APPLICATION = "LAUNCH_APPLICATION"
    FOCUS_APPLICATION = "FOCUS_APPLICATION"
    CLOSE_APPLICATION = "CLOSE_APPLICATION"
    SWITCH_APPLICATION = "SWITCH_APPLICATION"
    MINIMIZE_WINDOW = "MINIMIZE_WINDOW"
    MAXIMIZE_WINDOW = "MAXIMIZE_WINDOW"
    RESTORE_WINDOW = "RESTORE_WINDOW"

    # Browser & Web
    OPEN_URL = "OPEN_URL"
    NAVIGATE_URL = "NAVIGATE_URL"
    BROWSER_BACK = "BROWSER_BACK"
    BROWSER_FORWARD = "BROWSER_FORWARD"
    BROWSER_REFRESH = "BROWSER_REFRESH"
    OPEN_TAB = "OPEN_TAB"
    CLOSE_TAB = "CLOSE_TAB"
    SWITCH_TAB = "SWITCH_TAB"
    SUBMIT_FORM = "SUBMIT_FORM"
    EXTRACT_PAGE_CONTENT = "EXTRACT_PAGE_CONTENT"

    # Mouse & Cursor
    CLICK = "CLICK"
    DOUBLE_CLICK = "DOUBLE_CLICK"
    RIGHT_CLICK = "RIGHT_CLICK"
    MOVE_MOUSE = "MOVE_MOUSE"
    DRAG_AND_DROP = "DRAG_AND_DROP"
    SCROLL = "SCROLL"

    # Keyboard
    TYPE_TEXT = "TYPE_TEXT"
    PRESS_KEY = "PRESS_KEY"
    HOTKEY = "HOTKEY"

    # FileSystem
    CREATE_FILE = "CREATE_FILE"
    CREATE_FOLDER = "CREATE_FOLDER"
    READ_FILE = "READ_FILE"
    WRITE_FILE = "WRITE_FILE"
    LIST_FILES = "LIST_FILES"
    SEARCH_FILES = "SEARCH_FILES"
    OPEN_FILE = "OPEN_FILE"
    COPY_FILE = "COPY_FILE"
    MOVE_FILE = "MOVE_FILE"
    RENAME_FILE = "RENAME_FILE"
    DELETE_FILE = "DELETE_FILE"
    COMPRESS_FILES = "COMPRESS_FILES"
    EXTRACT_ARCHIVE = "EXTRACT_ARCHIVE"

    # Content Intelligence
    EXTRACT_DOCUMENT = "EXTRACT_DOCUMENT"
    SUMMARIZE_DOCUMENT = "SUMMARIZE_DOCUMENT"
    SEARCH_DOCUMENT = "SEARCH_DOCUMENT"
    QA_DOCUMENT = "QA_DOCUMENT"
    CREATE_DOCX = "CREATE_DOCX"
    CREATE_XLSX = "CREATE_XLSX"
    CREATE_PPTX = "CREATE_PPTX"
    ANALYZE_SHEET = "ANALYZE_SHEET"

    # Utility & Feedback
    WAIT = "WAIT"
    LOCATE = "LOCATE"
    HIGHLIGHT = "HIGHLIGHT"
    SPEAK = "SPEAK"


@dataclass
class Action:
    """Represents one atomic computer interaction."""

    action_type: str

    target: str | None = None

    value: Any = None

    parameters: dict[str, Any] = field(
        default_factory=dict
    )

    description: str | None = None

    verification: dict[str, Any] = field(
        default_factory=dict
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    resolved: bool = False

    execution_result: dict[str, Any] = field(
        default_factory=dict
    )

    # Whole-PC workflow dependencies
    action_id: str | None = None
    dependencies: list[str] = field(default_factory=list)
    prerequisites_met: bool = True