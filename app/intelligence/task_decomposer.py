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


class TaskDecomposer(RuleBasedTaskDecomposer):
    """Backward-compatible name used by existing code/tests."""

    pass