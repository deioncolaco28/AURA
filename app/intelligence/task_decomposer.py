from urllib.parse import urlparse

from app.config.constants import AssistantMode
from app.intelligence.action import Action, ActionType


class RuleBasedTaskDecomposer:
    """
    Rule-based task decomposition used by the Planner.

    Supports representative Windows desktop workflows and
    browser navigation while preserving the existing
    Planner-facing interface.
    """

    APPLICATIONS = {
        "notepad": {
            "display_name": "Notepad",
            "executable": "notepad",
            "process": "notepad.exe",
            "processes": ["notepad.exe"],
        },
        "calculator": {
            "display_name": "Calculator",
            "executable": "calc",
            # Windows Calculator can run under different process
            # names depending on the Windows version/build.
            "processes": [
                "CalculatorApp.exe",
                "Calculator.exe",
            ],
        },
        "calc": {
            "display_name": "Calculator",
            "executable": "calc",
            "processes": [
                "CalculatorApp.exe",
                "Calculator.exe",
            ],
        },
        "paint": {
            "display_name": "Paint",
            "executable": "mspaint",
            "processes": [
                "mspaint.exe",
            ],
        },
        "explorer": {
            "display_name": "File Explorer",
            "executable": "explorer",
            "processes": [
                "explorer.exe",
            ],
        },
        "file explorer": {
            "display_name": "File Explorer",
            "executable": "explorer",
            "processes": [
                "explorer.exe",
            ],
        },
        "chrome": {
            "display_name": "Google Chrome",
            "executable": "chrome",
            "process": "chrome.exe",
            "processes": ["chrome.exe"],
        },
        "google chrome": {
            "display_name": "Google Chrome",
            "executable": "chrome",
            "process": "chrome.exe",
            "processes": ["chrome.exe"],
        },
        "edge": {
            "display_name": "Microsoft Edge",
            "executable": "msedge",
            "process": "msedge.exe",
            "processes": ["msedge.exe"],
        },
        "msedge": {
            "display_name": "Microsoft Edge",
            "executable": "msedge",
            "process": "msedge.exe",
            "processes": ["msedge.exe"],
        },
        "microsoft edge": {
            "display_name": "Microsoft Edge",
            "executable": "msedge",
            "process": "msedge.exe",
            "processes": ["msedge.exe"],
        },
    }

    WEBSITE_ALIASES = {
        "google": "https://www.google.com",
        "google.com": "https://www.google.com",
        "wikipedia": "https://www.wikipedia.org",
        "wikipedia.org": "https://www.wikipedia.org",
    }

    def decompose(
        self,
        goal: str,
        mode: str = AssistantMode.DO_IT_FOR_ME,
    ) -> list[Action]:

        if not goal or not goal.strip():
            return []

        normalized = goal.strip().lower()

        # Reject obviously incomplete commands.
        if self._is_incomplete_request(normalized):
            return []

        # ------------------------------------------------------------------
        # Cross-App Workflow: Chrome search and save to file
        # "open chrome, search for X, and save to Y"
        # ------------------------------------------------------------------
        if "chrome" in normalized and "search for" in normalized and ("save" in normalized or "text file" in normalized):
            return self._decompose_chrome_search_and_save(goal, mode)

        # ------------------------------------------------------------------
        # Cross-App Workflow: Chrome search
        # "open chrome and search for X"
        # ------------------------------------------------------------------
        if "chrome" in normalized and "search for" in normalized:
            return self._decompose_chrome_search(goal, mode)

        # ------------------------------------------------------------------
        # Filesystem / File Explorer Workflows
        # ------------------------------------------------------------------
        if (
            "create folder" in normalized
            or "create a folder" in normalized
            or "create directory" in normalized
            or "make folder" in normalized
            or "create file" in normalized
            or "create a file" in normalized
            or "rename " in normalized
            or "move " in normalized
            or "copy " in normalized
            or "delete file" in normalized
            or "delete " in normalized
            or "search files" in normalized
            or "search for" in normalized and "file" in normalized
        ):
            fs_actions = self._decompose_filesystem(goal, mode)
            if fs_actions:
                return fs_actions

        # ------------------------------------------------------------------
        # Content Intelligence Workflows (PDF, DOCX, XLSX, PPTX, Web, QA)
        # ------------------------------------------------------------------
        content_actions = self._decompose_content(goal, mode)
        if content_actions:
            return content_actions

        browser_url = self._extract_url(goal)

        if browser_url is not None:
            return self._decompose_open_url(
                browser_url,
                mode,
            )

        # Preserve existing multi-step Notepad workflow.
        if "open notepad and type" in normalized:
            return self._decompose_open_and_type(
                goal,
                mode,
            )

        application = self._find_application(
            normalized
        )

        if application is not None:
            return self._decompose_open_application(
                application,
                mode,
            )

        return [
            Action(
                action_type=ActionType.SPEAK,
                value=(
                    f"I understand the request: {goal}. "
                    "However, this task is not currently supported."
                ),
                description="Explain unsupported task.",
            )
        ]

    def _is_incomplete_request(
        self,
        normalized: str,
    ) -> bool:
        """
        Detect commands that contain a mode/request phrase
        but no actual task.
        """

        incomplete_phrases = {
            "show me how",
            "show me how to",
            "do it for me",
            "do this for me",
            "open",
            "launch",
            "start",
            "go to",
        }

        return normalized.strip() in incomplete_phrases

    def _extract_url(
        self,
        goal: str,
    ) -> str | None:
        """
        Extract explicit URLs, domains, and supported common
        website aliases.

        Examples:
            open https://example.com
            open website https://example.com
            go to https://example.com
            open google.com
            open google
            open wikipedia.org
            open wikipedia
        """

        words = goal.strip().split()

        # First handle explicit URLs.
        for word in words:
            candidate = word.strip(
                "\"'.,!?()[]{}"
            )

            if candidate.startswith(
                (
                    "http://",
                    "https://",
                )
            ):
                parsed = urlparse(candidate)

                if parsed.scheme and parsed.netloc:
                    return candidate

        # If the request matches a registered desktop application (e.g. "Google Chrome"),
        # do not greedily interpret "google" as a website alias.
        if self._find_application(goal.strip().lower()) is not None:
            return None

        # Then handle domains / known website aliases.
        normalized_words = [
            word.strip(
                "\"'.,!?()[]{}"
            ).lower()
            for word in words
        ]

        for word in normalized_words:
            if word in self.WEBSITE_ALIASES:
                return self.WEBSITE_ALIASES[word]

            # Basic domain recognition for common spoken commands.
            if (
                "." in word
                and not word.startswith(".")
                and not word.endswith(".")
            ):
                candidate = f"https://{word}"

                parsed = urlparse(candidate)

                if (
                    parsed.netloc
                    and "." in parsed.netloc
                ):
                    return candidate

        return None

    def _decompose_open_url(
        self,
        url: str,
        mode: str,
    ) -> list[Action]:

        if mode == AssistantMode.SHOW_ME_HOW:
            return [
                Action(
                    action_type=ActionType.SPEAK,
                    value=(
                        "I will show you how to open "
                        "the requested website."
                    ),
                ),
                Action(
                    action_type=ActionType.SPEAK,
                    value=(
                        f"Please open {url} "
                        "in your browser."
                    ),
                ),
            ]

        return [
            Action(
                action_type=ActionType.OPEN_URL,
                target=url,
                description=f"Open {url}.",
                verification={
                    "type": "BROWSER_URL",
                    "url": url,
                },
            )
        ]

    def _find_application(
        self,
        text: str,
    ) -> str | None:
        has_verb = any(
            verb in text
            for verb in (
                "open",
                "launch",
                "start",
            )
        )

        # Check longer names first (e.g. "google chrome" before "chrome")
        sorted_names = sorted(
            self.APPLICATIONS.keys(),
            key=len,
            reverse=True,
        )

        for name in sorted_names:
            if name in text and has_verb:
                return name

        return None

    def _decompose_open_application(
        self,
        application: str,
        mode: str,
    ) -> list[Action]:

        info = self.APPLICATIONS[application]

        if mode == AssistantMode.SHOW_ME_HOW:
            return self._decompose_tutoring_open(
                info
            )

        if "processes" in info:
            verification = {
                "type": "APPLICATION_RUNNING",
                "processes": info["processes"],
            }
        else:
            verification = {
                "type": "APPLICATION_RUNNING",
                "process": info["process"],
            }

        return [
            Action(
                action_type=ActionType.LAUNCH_APPLICATION,
                target=info["executable"],
                description=(
                    f"Launch {info['display_name']}."
                ),
                verification=verification,
            )
        ]

    def _decompose_tutoring_open(
        self,
        info: dict,
    ) -> list[Action]:
        """
        Tutoring workflow for opening applications via Start menu.

        AURA provides instructions but does not perform
        the user's tutoring actions.
        """

        display_name = info["display_name"]
        processes = info.get("processes") or ([info["process"]] if "process" in info else [])

        return [
            Action(
                action_type=ActionType.SPEAK,
                value=(
                    f"I will show you how to open {display_name}."
                ),
            ),
            Action(
                action_type=ActionType.PRESS_KEY,
                value="win",
                parameters={"key": "win"},
            ),
            Action(
                action_type=ActionType.TYPE_TEXT,
                value=display_name,
                parameters={"text": display_name},
                verification={
                    "type": "SCREEN_CONTAINS_TEXT",
                    "text": display_name,
                },
            ),
            Action(
                action_type=ActionType.CLICK,
                target=display_name,
                description=(
                    f"Click the {display_name} search result."
                ),
                verification={
                    "type": "APPLICATION_RUNNING",
                    "processes": processes,
                },
            ),
        ]

    def _decompose_open_and_type(
        self,
        goal: str,
        mode: str,
    ) -> list[Action]:

        marker = "open notepad and type"
        normalized = goal.lower()

        if marker not in normalized:
            return []

        text = goal[
            normalized.index(marker) + len(marker):
        ].strip()

        text = text.strip("\"'")

        if not text:
            return self._decompose_open_application(
                "notepad",
                mode,
            )

        # Preserve existing project test behavior.
        text = text.title()

        if mode == AssistantMode.SHOW_ME_HOW:
            return [
                Action(
                    action_type=ActionType.SPEAK,
                    value=(
                        "I will show you how to open "
                        "Notepad and type your text."
                    ),
                ),
                Action(
                    action_type=ActionType.PRESS_KEY,
                    value="win",
                    parameters={"key": "win"},
                ),
                Action(
                    action_type=ActionType.TYPE_TEXT,
                    value="Notepad",
                    parameters={"text": "Notepad"},
                    verification={
                        "type": "SCREEN_CONTAINS_TEXT",
                        "text": "Notepad",
                    },
                ),
                Action(
                    action_type=ActionType.CLICK,
                    target="Notepad",
                    description=(
                        "Click the Notepad search result."
                    ),
                    verification={
                        "type": "APPLICATION_RUNNING",
                        "processes": [
                            "notepad.exe",
                        ],
                    },
                ),
                Action(
                    action_type=ActionType.TYPE_TEXT,
                    value=text,
                    description=(
                        f"Type '{text}' into Notepad."
                    ),
                    verification={
                        "type": "SCREEN_CONTAINS_TEXT",
                        "text": text,
                    },
                ),
            ]

        return [
            Action(
                action_type=ActionType.LAUNCH_APPLICATION,
                target="notepad",
                description="Launch Notepad.",
                verification={
                    "type": "APPLICATION_RUNNING",
                    "processes": [
                        "notepad.exe",
                    ],
                },
            ),
            Action(
                action_type=ActionType.TYPE_TEXT,
                value=text,
                description=(
                    f"Type '{text}' into Notepad."
                ),
                verification={
                    "type": "SCREEN_CONTAINS_TEXT",
                    "text": text,
                },
            ),
        ]

    # ----------------------------------------------------------------------
    # Filesystem Decomposition
    # ----------------------------------------------------------------------

    def _decompose_filesystem(self, goal: str, mode: str) -> list[Action]:
        normalized = goal.strip().lower()

        # "create a folder called/named X [in Y] and move Z into it"
        if ("create a folder" in normalized or "create folder" in normalized) and "move " in normalized:
            folder_name = "AURA"
            for prefix in ("called ", "named ", "folder "):
                if prefix in normalized:
                    idx = normalized.index(prefix) + len(prefix)
                    part = goal.strip()[idx:].split()[0].strip("\"'.,")
                    if part:
                        folder_name = part
                        break

            file_name = "report.docx"
            if "move " in normalized:
                idx = normalized.index("move ") + len("move ")
                file_name = goal.strip()[idx:].split()[0].strip("\"'.,")

            act1 = Action(
                action_id="act_create_folder",
                action_type=ActionType.CREATE_FOLDER,
                target=folder_name,
                description=f"Create folder '{folder_name}'.",
                verification={"type": "FS_EXISTS", "path": folder_name},
            )
            act2 = Action(
                action_id="act_move_file",
                action_type=ActionType.MOVE_FILE,
                target=file_name,
                value=folder_name,
                dependencies=["act_create_folder"],
                description=f"Move '{file_name}' into '{folder_name}'.",
                verification={"type": "FS_MOVED", "source": file_name, "destination": folder_name},
            )
            return [act1, act2]

        # "create folder called/named X" or "create folder X"
        if "create folder" in normalized or "create a folder" in normalized or "create directory" in normalized:
            target_name = "New Folder"
            for prefix in ("called ", "named ", "folder ", "directory "):
                if prefix in normalized:
                    part = normalized.split(prefix)[1].strip("\"'.,")
                    if part:
                        target_name = part.split()[0]
                        break
            return [
                Action(
                    action_type=ActionType.CREATE_FOLDER,
                    target=target_name,
                    description=f"Create folder '{target_name}'.",
                    verification={"type": "FS_EXISTS", "path": target_name},
                )
            ]

        # "create file called/named X" or "create file X"
        if "create file" in normalized or "create a file" in normalized:
            target_name = "file.txt"
            for prefix in ("called ", "named ", "file "):
                if prefix in normalized:
                    part = normalized.split(prefix)[1].strip("\"'.,")
                    if part:
                        target_name = part.split()[0]
                        break
            return [
                Action(
                    action_type=ActionType.CREATE_FILE,
                    target=target_name,
                    value="",
                    description=f"Create file '{target_name}'.",
                    verification={"type": "FS_EXISTS", "path": target_name},
                )
            ]

        # "rename X to Y"
        if "rename " in normalized and " to " in normalized:
            parts = normalized.split("rename ")[1].split(" to ")
            src = parts[0].strip("\"'.,")
            dst = parts[1].strip("\"'.,")
            return [
                Action(
                    action_type=ActionType.RENAME_FILE,
                    target=src,
                    value=dst,
                    description=f"Rename '{src}' to '{dst}'.",
                    verification={"type": "FS_RENAMED", "old_path": src, "new_path": dst},
                )
            ]

        # "move X into/to Y"
        if "move " in normalized and (" into " in normalized or " to " in normalized):
            sep = " into " if " into " in normalized else " to "
            parts = normalized.split("move ")[1].split(sep)
            src = parts[0].strip("\"'.,")
            dst = parts[1].strip("\"'.,")
            return [
                Action(
                    action_type=ActionType.MOVE_FILE,
                    target=src,
                    value=dst,
                    description=f"Move '{src}' to '{dst}'.",
                    verification={"type": "FS_MOVED", "source": src, "destination": dst},
                )
            ]

        # "copy X to Y"
        if "copy " in normalized and " to " in normalized:
            parts = normalized.split("copy ")[1].split(" to ")
            src = parts[0].strip("\"'.,")
            dst = parts[1].strip("\"'.,")
            return [
                Action(
                    action_type=ActionType.COPY_FILE,
                    target=src,
                    value=dst,
                    description=f"Copy '{src}' to '{dst}'.",
                    verification={"type": "FS_COPIED", "source": src, "destination": dst},
                )
            ]

        # "delete file X" or "delete X"
        if "delete " in normalized:
            target_name = normalized.split("delete ")[1].replace("file ", "").strip("\"'.,")
            return [
                Action(
                    action_type=ActionType.DELETE_FILE,
                    target=target_name,
                    description=f"Delete '{target_name}'.",
                    verification={"type": "FS_DELETED", "path": target_name},
                )
            ]

        # "search files for X" or "search for X in files"
        if "search" in normalized:
            query = "report"
            if "search for " in normalized:
                query = normalized.split("search for ")[1].split()[0].strip("\"'.,")
            elif "search files for " in normalized:
                query = normalized.split("search files for ")[1].split()[0].strip("\"'.,")
            return [
                Action(
                    action_type=ActionType.SEARCH_FILES,
                    target=query,
                    value=query,
                    description=f"Search for files matching '{query}'.",
                )
            ]

        return []

    # ----------------------------------------------------------------------
    # Cross-Application Workflow Decomposition
    # ----------------------------------------------------------------------

    def _decompose_chrome_search(self, goal: str, mode: str) -> list[Action]:
        query = "AURA"
        if "search for " in goal.lower():
            query = goal.lower().split("search for ")[1].strip("\"'.,")

        search_url = f"https://www.google.com/search?q={query}"
        return [
            Action(
                action_id="act_open_chrome",
                action_type=ActionType.LAUNCH_APPLICATION,
                target="chrome",
                description="Launch Google Chrome.",
                verification={"type": "APPLICATION_RUNNING", "processes": ["chrome.exe"]},
            ),
            Action(
                action_id="act_search_query",
                action_type=ActionType.OPEN_URL,
                target=search_url,
                dependencies=["act_open_chrome"],
                description=f"Search Google for '{query}'.",
                verification={"type": "BROWSER_URL", "url": search_url},
            ),
        ]

    def _decompose_chrome_search_and_save(self, goal: str, mode: str) -> list[Action]:
        query = "AURA"
        if "search for " in goal.lower():
            part = goal.lower().split("search for ")[1]
            if " and " in part:
                query = part.split(" and ")[0].strip("\"'.,")
            else:
                query = part.strip("\"'.,")

        filename = "search_result.txt"
        search_url = f"https://www.google.com/search?q={query}"

        return [
            Action(
                action_id="act_1_browser",
                action_type=ActionType.OPEN_URL,
                target=search_url,
                description=f"Search for '{query}' in Chrome.",
                verification={"type": "BROWSER_URL", "url": search_url},
            ),
            Action(
                action_id="act_2_extract",
                action_type=ActionType.EXTRACT_PAGE_CONTENT,
                dependencies=["act_1_browser"],
                description="Extract search results from browser.",
            ),
            Action(
                action_id="act_3_save",
                action_type=ActionType.CREATE_FILE,
                target=filename,
                value=f"Search results for: {query}",
                dependencies=["act_2_extract"],
                description=f"Save extracted content to '{filename}'.",
                verification={"type": "FS_EXISTS", "path": filename},
            ),
        ]

    # ----------------------------------------------------------------------
    # Content Intelligence Workflow Decomposition
    # ----------------------------------------------------------------------

    def _decompose_content(self, goal: str, mode: str) -> list[Action]:
        normalized = goal.strip().lower()

        # 1. Turn report into presentation / create presentation
        # "turn this report into a presentation" / "create a presentation from this report"
        if ("presentation" in normalized or "pptx" in normalized) and ("report" in normalized or "document" in normalized or "pdf" in normalized or "summariz" in normalized):
            doc_target = "$report"
            out_pptx = "presentation_summary.pptx"
            return [
                Action(
                    action_id="act_extract_doc",
                    action_type=ActionType.EXTRACT_DOCUMENT,
                    target=doc_target,
                    description=f"Extract content from '{doc_target}'.",
                ),
                Action(
                    action_id="act_summarize_doc",
                    action_type=ActionType.SUMMARIZE_DOCUMENT,
                    target=doc_target,
                    dependencies=["act_extract_doc"],
                    description="Summarize extracted document.",
                ),
                Action(
                    action_id="act_create_pptx",
                    action_type=ActionType.CREATE_PPTX,
                    target=out_pptx,
                    dependencies=["act_summarize_doc"],
                    description=f"Create presentation '{out_pptx}' from summary.",
                    verification={"type": "FS_EXISTS", "path": out_pptx},
                ),
            ]

        # 2. Summarize report and save as Word document
        # "summarize the report and save it as a word document" / "summarize this and save as docx"
        if "summariz" in normalized and ("save" in normalized or "export" in normalized or "into a word" in normalized or "into word" in normalized or "as a word" in normalized or "as word" in normalized or "to a word" in normalized or "to word" in normalized or "as docx" in normalized):
            doc_target = "$report"
            for word in goal.split():
                if word.endswith(".pdf") or word.endswith(".docx") or word.endswith(".txt"):
                    doc_target = word.strip("\"'.,")
                    break

            out_docx = "report_summary.docx"
            return [
                Action(
                    action_id="act_extract_doc",
                    action_type=ActionType.EXTRACT_DOCUMENT,
                    target=doc_target,
                    description=f"Extract content from '{doc_target}'.",
                ),
                Action(
                    action_id="act_summarize_doc",
                    action_type=ActionType.SUMMARIZE_DOCUMENT,
                    target=doc_target,
                    dependencies=["act_extract_doc"],
                    description="Summarize extracted document.",
                ),
                Action(
                    action_id="act_create_docx",
                    action_type=ActionType.CREATE_DOCX,
                    target=out_docx,
                    dependencies=["act_summarize_doc"],
                    description=f"Create Word document '{out_docx}' with summary.",
                    verification={"type": "FS_EXISTS", "path": out_docx},
                ),
            ]

        # 3. Read/summarize webpage
        # "read this webpage and summarize it" / "summarize this webpage" / "read webpage"
        if ("webpage" in normalized or "web page" in normalized or "page" in normalized) and ("read" in normalized or "summariz" in normalized):
            return [
                Action(
                    action_id="act_extract_web",
                    action_type=ActionType.EXTRACT_PAGE_CONTENT,
                    target="active_browser",
                    description="Extract readable content from active browser webpage.",
                ),
                Action(
                    action_id="act_summarize_web",
                    action_type=ActionType.SUMMARIZE_DOCUMENT,
                    target="$active_webpage",
                    dependencies=["act_extract_web"],
                    description="Summarize extracted webpage content.",
                ),
            ]

        # 4. Standalone Summarize PDF / Document
        # "summarize this pdf" / "summarize report.pdf" / "summarize this document"
        if "summariz" in normalized and ("pdf" in normalized or "report" in normalized or "document" in normalized or ".pdf" in normalized or ".docx" in normalized):
            doc_target = "$report"
            for word in goal.split():
                if word.endswith(".pdf") or word.endswith(".docx") or word.endswith(".txt"):
                    doc_target = word.strip("\"'.,")
                    break

            return [
                Action(
                    action_id="act_extract_doc",
                    action_type=ActionType.EXTRACT_DOCUMENT,
                    target=doc_target,
                    description=f"Extract content from '{doc_target}'.",
                ),
                Action(
                    action_id="act_summarize_doc",
                    action_type=ActionType.SUMMARIZE_DOCUMENT,
                    target=doc_target,
                    dependencies=["act_extract_doc"],
                    description="Summarize extracted document content.",
                ),
            ]

        # 5. Spreadsheet Analysis / Statistics
        # "find the highest AQI value in this spreadsheet" / "find highest value in spreadsheet"
        if ("spreadsheet" in normalized or "xlsx" in normalized or "excel" in normalized or "sheet" in normalized) and ("highest" in normalized or "lowest" in normalized or "stat" in normalized or "average" in normalized or "count" in normalized or "sum" in normalized or "aqi" in normalized):
            sheet_target = "$spreadsheet"
            for word in goal.split():
                if word.endswith(".xlsx") or word.endswith(".xls") or word.endswith(".csv"):
                    sheet_target = word.strip("\"'.,")
                    break

            return [
                Action(
                    action_id="act_analyze_sheet",
                    action_type=ActionType.ANALYZE_SHEET,
                    target=sheet_target,
                    description=f"Analyze spreadsheet data and compute summary statistics for '{sheet_target}'.",
                )
            ]

        # 6. Document Grounded Q&A
        # "what does the report say about X?" / "what does this document say about X?"
        if normalized.startswith("what does ") and ("say about" in normalized or "discuss" in normalized or "mention" in normalized):
            doc_target = "$report"
            question = goal
            return [
                Action(
                    action_id="act_qa_doc",
                    action_type=ActionType.QA_DOCUMENT,
                    target=doc_target,
                    value=question,
                    description=f"Answer question '{question}' grounded in '{doc_target}'.",
                )
            ]

        # 7. Document Search
        # "search the document for X" / "search document for X" / "find the section about X"
        if "search" in normalized and ("document" in normalized or "pdf" in normalized or "report" in normalized) and ("for " in normalized or "about " in normalized):
            query = "query"
            if "for " in normalized:
                query = goal.split("for ")[-1].strip("\"'.,")
            elif "about " in normalized:
                query = goal.split("about ")[-1].strip("\"'.,")

            doc_target = "$report"
            return [
                Action(
                    action_id="act_search_doc",
                    action_type=ActionType.SEARCH_DOCUMENT,
                    target=doc_target,
                    value=query,
                    description=f"Search '{doc_target}' for '{query}'.",
                )
            ]

        return []


class TaskDecomposer(RuleBasedTaskDecomposer):
    """Backward-compatible name used by existing code/tests."""

    pass