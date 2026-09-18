from app.automation.application_manager import ApplicationManager
from app.automation.browser import BrowserController
from app.automation.browser_manager import BrowserManager
from app.automation.controller import ComputerController
from app.automation.desktop_manager import DesktopManager
from app.automation.filesystem_manager import FileSystemManager
from app.content.content_manager import ContentManager
from app.intelligence.action import Action, ActionType


class ActionExecutor:
    """Executes validated atomic computer actions across Desktop, Browser, Filesystem, Applications, and Content."""

    def __init__(
        self,
        controller: ComputerController | None = None,
        browser_controller: BrowserController | None = None,
        desktop_manager: DesktopManager | None = None,
        application_manager: ApplicationManager | None = None,
        filesystem_manager: FileSystemManager | None = None,
        browser_manager: BrowserManager | None = None,
        content_manager: ContentManager | None = None,
    ):
        self.controller = controller or ComputerController()
        self.browser_controller = browser_controller or BrowserController()
        self.desktop_manager = desktop_manager or DesktopManager()
        self.application_manager = application_manager or ApplicationManager()
        self.filesystem_manager = filesystem_manager or FileSystemManager()
        self.browser_manager = browser_manager or BrowserManager(controller=self.browser_controller)
        self.content_manager = content_manager or ContentManager()

    def execute(
        self,
        action: Action,
    ) -> None:
        """Execute one action."""

        action_type = action.action_type

        # Application & Window
        if action_type == ActionType.LAUNCH_APPLICATION:
            self._launch_application(action)
        elif action_type == ActionType.FOCUS_APPLICATION:
            self._focus_application(action)
        elif action_type == ActionType.CLOSE_APPLICATION:
            self._close_application(action)
        elif action_type == ActionType.SWITCH_APPLICATION:
            self.desktop_manager.switch_application()
        elif action_type == ActionType.MINIMIZE_WINDOW:
            self.desktop_manager.minimize_window(action.target)
        elif action_type == ActionType.MAXIMIZE_WINDOW:
            self.desktop_manager.maximize_window(action.target)
        elif action_type == ActionType.RESTORE_WINDOW:
            self.desktop_manager.restore_window(action.target)

        # Browser & Web
        elif action_type in (ActionType.OPEN_URL, ActionType.NAVIGATE_URL):
            self._open_url(action)
        elif action_type == ActionType.BROWSER_BACK:
            self.browser_manager.back()
        elif action_type == ActionType.BROWSER_FORWARD:
            self.browser_manager.forward()
        elif action_type == ActionType.BROWSER_REFRESH:
            self.browser_manager.refresh()
        elif action_type == ActionType.OPEN_TAB:
            self.browser_manager.open_tab(action.target)
        elif action_type == ActionType.CLOSE_TAB:
            self.browser_manager.close_tab()
        elif action_type == ActionType.SWITCH_TAB:
            idx = int(action.value or 0)
            self.browser_manager.switch_tab(idx)
        elif action_type == ActionType.SUBMIT_FORM:
            self.browser_manager.submit(action.target)
        elif action_type == ActionType.EXTRACT_PAGE_CONTENT:
            content = self.browser_manager.extract_content()
            action.execution_result["extracted_content"] = content

        # Mouse & Cursor
        elif action_type == ActionType.CLICK:
            self._click(action)
        elif action_type == ActionType.DOUBLE_CLICK:
            self._double_click(action)
        elif action_type == ActionType.RIGHT_CLICK:
            self._right_click(action)
        elif action_type == ActionType.MOVE_MOUSE:
            self._move_mouse(action)
        elif action_type == ActionType.DRAG_AND_DROP:
            self._drag_and_drop(action)
        elif action_type == ActionType.SCROLL:
            delta = int(action.value or action.parameters.get("delta", -400))
            self.desktop_manager.scroll(delta)

        # Keyboard
        elif action_type == ActionType.TYPE_TEXT:
            self._type_text(action)
        elif action_type == ActionType.PRESS_KEY:
            self._press_key(action)
        elif action_type == ActionType.HOTKEY:
            self._hotkey(action)

        # FileSystem
        elif action_type == ActionType.CREATE_FILE:
            self._create_file(action)
        elif action_type == ActionType.CREATE_FOLDER:
            self._create_folder(action)
        elif action_type == ActionType.READ_FILE:
            self._read_file(action)
        elif action_type == ActionType.WRITE_FILE:
            self._write_file(action)
        elif action_type == ActionType.LIST_FILES:
            self._list_files(action)
        elif action_type == ActionType.SEARCH_FILES:
            self._search_files(action)
        elif action_type == ActionType.OPEN_FILE:
            self._open_file(action)
        elif action_type == ActionType.COPY_FILE:
            self._copy_file(action)
        elif action_type == ActionType.MOVE_FILE:
            self._move_file(action)
        elif action_type == ActionType.RENAME_FILE:
            self._rename_file(action)
        elif action_type == ActionType.DELETE_FILE:
            self._delete_file(action)
        elif action_type == ActionType.COMPRESS_FILES:
            self._compress_files(action)
        elif action_type == ActionType.EXTRACT_ARCHIVE:
            self._extract_archive(action)

        # Content Intelligence
        elif action_type == ActionType.EXTRACT_DOCUMENT:
            doc = self.content_manager.extract(action.target)
            action.execution_result["document"] = doc
            action.execution_result["extracted_text"] = doc.full_text
            action.execution_result["word_count"] = doc.word_count
        elif action_type == ActionType.SUMMARIZE_DOCUMENT:
            max_points = action.parameters.get("max_points", 5)
            section_filter = action.parameters.get("section_filter")
            summary = self.content_manager.summarize(action.target, max_points=max_points, section_filter=section_filter)
            action.execution_result["summary"] = summary
            action.execution_result["summary_text"] = summary.summary_text
            action.execution_result["key_points"] = summary.key_points
        elif action_type == ActionType.SEARCH_DOCUMENT:
            query = str(action.value or action.parameters.get("query", ""))
            results = self.content_manager.search(action.target, query)
            action.execution_result["search_results"] = results
            action.execution_result["match_count"] = len(results)
        elif action_type == ActionType.QA_DOCUMENT:
            question = str(action.value or action.parameters.get("question", ""))
            qa = self.content_manager.answer_question(action.target, question)
            action.execution_result["qa_result"] = qa
            action.execution_result["answer"] = qa.answer
            action.execution_result["is_grounded"] = qa.is_grounded
        elif action_type == ActionType.CREATE_DOCX:
            title = action.parameters.get("title", "Document")
            created = self.content_manager.create_document(
                "DOCX",
                action.target,
                title=title,
                content=action.value,
                key_points=action.parameters.get("key_points"),
            )
            action.execution_result["created_path"] = created
        elif action_type == ActionType.CREATE_XLSX:
            headers = action.parameters.get("headers", [])
            rows = action.parameters.get("rows", [])
            created = self.content_manager.create_document("XLSX", action.target, headers=headers, rows=rows)
            action.execution_result["created_path"] = created
        elif action_type == ActionType.CREATE_PPTX:
            title = action.parameters.get("title", "Presentation")
            slides = action.parameters.get("slides")
            key_points = action.parameters.get("key_points")
            created = self.content_manager.create_document("PPTX", action.target, title=title, slides=slides, key_points=key_points)
            action.execution_result["created_path"] = created
        elif action_type == ActionType.ANALYZE_SHEET:
            sheet_name = action.parameters.get("sheet_name")
            col = action.parameters.get("column")
            stats = self.content_manager.analyze_spreadsheet(action.target, sheet_name=sheet_name, column=col)
            action.execution_result["stats"] = stats

        # Utility
        elif action_type == ActionType.WAIT:
            self._wait(action)

        else:
            raise ValueError(
                f"Unsupported executable action: "
                f"{action_type}"
            )

    # ----------------------------------------------------------------------
    # Filesystem Helpers
    # ----------------------------------------------------------------------

    def _create_file(self, action: Action) -> None:
        if not action.target:
            raise ValueError("CREATE_FILE requires a target path.")
        content = str(action.value or "")
        created = self.filesystem_manager.create_file(action.target, content)
        action.execution_result["created_path"] = created

    def _create_folder(self, action: Action) -> None:
        if not action.target:
            raise ValueError("CREATE_FOLDER requires a target path.")
        created = self.filesystem_manager.create_folder(action.target)
        action.execution_result["created_path"] = created

    def _read_file(self, action: Action) -> None:
        if not action.target:
            raise ValueError("READ_FILE requires a target path.")
        max_bytes = action.parameters.get("max_bytes")
        content = self.filesystem_manager.read_file(action.target, max_bytes=max_bytes)
        action.execution_result["content"] = content

    def _write_file(self, action: Action) -> None:
        if not action.target:
            raise ValueError("WRITE_FILE requires a target path.")
        content = str(action.value or "")
        overwrite = action.parameters.get("overwrite", True)
        written = self.filesystem_manager.write_file(action.target, content, overwrite=overwrite)
        action.execution_result["written_path"] = written

    def _list_files(self, action: Action) -> None:
        path = action.target or "."
        recursive = action.parameters.get("recursive", False)
        pattern = action.parameters.get("pattern")
        files = self.filesystem_manager.list_directory(path=path, recursive=recursive, pattern=pattern)
        action.execution_result["files"] = files

    def _search_files(self, action: Action) -> None:
        query = str(action.value or action.target or "")
        directory = action.parameters.get("directory", ".")
        file_type = action.parameters.get("file_type")
        candidates = self.filesystem_manager.search_files(query=query, directory=directory, file_type=file_type)
        action.execution_result["candidates"] = candidates

    def _open_file(self, action: Action) -> None:
        if not action.target:
            raise ValueError("OPEN_FILE requires a target path.")
        self.filesystem_manager.open_path(action.target)

    def _copy_file(self, action: Action) -> None:
        src = action.target
        dst = action.value or action.parameters.get("destination")
        if not src or not dst:
            raise ValueError("COPY_FILE requires source and destination.")
        copied = self.filesystem_manager.copy_path(src, dst)
        action.execution_result["copied_path"] = copied

    def _move_file(self, action: Action) -> None:
        src = action.target
        dst = action.value or action.parameters.get("destination")
        if not src or not dst:
            raise ValueError("MOVE_FILE requires source and destination.")
        moved = self.filesystem_manager.move_path(src, dst)
        action.execution_result["moved_path"] = moved

    def _rename_file(self, action: Action) -> None:
        src = action.target
        new_name = action.value or action.parameters.get("new_name")
        if not src or not new_name:
            raise ValueError("RENAME_FILE requires source and new_name.")
        renamed = self.filesystem_manager.rename_path(src, new_name)
        action.execution_result["renamed_path"] = renamed

    def _delete_file(self, action: Action) -> None:
        if not action.target:
            raise ValueError("DELETE_FILE requires a target path.")
        self.filesystem_manager.delete_path(action.target)

    def _compress_files(self, action: Action) -> None:
        sources = action.parameters.get("sources", [action.target])
        dst = action.value or action.parameters.get("destination")
        if not dst:
            raise ValueError("COMPRESS_FILES requires destination archive path.")
        zip_path = self.filesystem_manager.compress_archive(sources, dst)
        action.execution_result["archive_path"] = zip_path

    def _extract_archive(self, action: Action) -> None:
        src = action.target
        dst = action.value or action.parameters.get("destination", ".")
        if not src:
            raise ValueError("EXTRACT_ARCHIVE requires source archive path.")
        extracted = self.filesystem_manager.extract_archive(src, dst)
        action.execution_result["extracted_dir"] = extracted

    # ----------------------------------------------------------------------
    # Application Helpers
    # ----------------------------------------------------------------------

    def _focus_application(self, action: Action) -> None:
        if not action.target:
            raise ValueError("FOCUS_APPLICATION requires a target.")
        self.application_manager.focus(action.target)

    def _close_application(self, action: Action) -> None:
        if not action.target:
            raise ValueError("CLOSE_APPLICATION requires a target.")
        self.application_manager.close(action.target)

    def _right_click(self, action: Action) -> None:
        x = action.parameters.get("x")
        y = action.parameters.get("y")
        self.desktop_manager.right_click(x=x, y=y)

    def _drag_and_drop(self, action: Action) -> None:
        start_x = action.parameters.get("start_x")
        start_y = action.parameters.get("start_y")
        end_x = action.parameters.get("end_x", action.parameters.get("x"))
        end_y = action.parameters.get("end_y", action.parameters.get("y"))
        if start_x is None or start_y is None or end_x is None or end_y is None:
            raise ValueError("DRAG_AND_DROP requires start (x, y) and end (x, y) coordinates.")
        self.desktop_manager.drag_and_drop((start_x, start_y), (end_x, end_y))

    def _hotkey(self, action: Action) -> None:
        keys = action.parameters.get("keys")
        if not keys and action.value:
            keys = [action.value] if isinstance(action.value, str) else list(action.value)
        if not keys:
            raise ValueError("HOTKEY requires keys.")
        self.desktop_manager.hotkey(*keys)

    def _launch_application(
        self,
        action: Action,
    ) -> None:
        if not action.target:
            raise ValueError(
                "LAUNCH_APPLICATION "
                "requires a target."
            )

        self.controller.launch_application(
            action.target
        )

        time.sleep(
            action.parameters.get(
                "startup_wait",
                1.0,
            )
        )

    def _open_url(
        self,
        action: Action,
    ) -> None:
        if not action.target:
            raise ValueError(
                "OPEN_URL requires a target."
            )

        result = self.browser_controller.open_url(
            action.target
        )

        action.execution_result.update(
            {
                "browser_success": result.success,
                "url": result.url,
                "message": result.message,
            }
        )

        if not result.success:
            raise RuntimeError(
                result.message
                or "Browser navigation failed."
            )

    def _click(
        self,
        action: Action,
    ) -> None:
        x = action.parameters.get("x")
        y = action.parameters.get("y")

        if x is None or y is None:
            raise ValueError(
                "CLICK requires resolved "
                "x and y coordinates."
            )

        self.controller.click(
            x,
            y,
        )

    def _double_click(
        self,
        action: Action,
    ) -> None:
        x = action.parameters.get("x")
        y = action.parameters.get("y")

        if x is None or y is None:
            raise ValueError(
                "DOUBLE_CLICK requires "
                "resolved x and y coordinates."
            )

        self.controller.double_click(
            x,
            y,
        )

    def _type_text(
        self,
        action: Action,
    ) -> None:
        if action.value is None:
            raise ValueError(
                "TYPE_TEXT requires a value."
            )

        self.controller.type_text(
            str(action.value)
        )

    def _press_key(
        self,
        action: Action,
    ) -> None:
        if not action.value:
            raise ValueError(
                "PRESS_KEY requires a key."
            )

        self.controller.press(
            str(action.value)
        )

    def _move_mouse(
        self,
        action: Action,
    ) -> None:
        x = action.parameters.get("x")
        y = action.parameters.get("y")

        if x is None or y is None:
            raise ValueError(
                "MOVE_MOUSE requires "
                "resolved x and y coordinates."
            )

        self.controller.move_mouse(
            x,
            y,
        )

    def _wait(
        self,
        action: Action,
    ) -> None:
        seconds = action.parameters.get(
            "seconds",
            1.0,
        )

        self.controller.wait(
            seconds
        )