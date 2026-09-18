"""
app/automation/environments/filesystem_environment.py

FileSystem execution environment for local file, folder, and archive operations.
"""

from __future__ import annotations

from typing import Any
from app.automation.environments.environment import Environment, EnvironmentCapability


class FileSystemEnvironment(Environment):
    """
    Execution environment for filesystem interactions (CRUD, search, compression).
    """

    def __init__(self, filesystem_manager: Any = None):
        self._filesystem_manager = filesystem_manager

    @property
    def name(self) -> str:
        return "filesystem"

    def supported_capabilities(self) -> set[EnvironmentCapability]:
        return {
            EnvironmentCapability.FS_LIST,
            EnvironmentCapability.FS_SEARCH,
            EnvironmentCapability.FS_CREATE_FILE,
            EnvironmentCapability.FS_CREATE_FOLDER,
            EnvironmentCapability.FS_READ,
            EnvironmentCapability.FS_WRITE,
            EnvironmentCapability.FS_OPEN,
            EnvironmentCapability.FS_COPY,
            EnvironmentCapability.FS_MOVE,
            EnvironmentCapability.FS_RENAME,
            EnvironmentCapability.FS_DELETE,
            EnvironmentCapability.FS_COMPRESS,
            EnvironmentCapability.FS_EXTRACT,
        }

    @property
    def filesystem_manager(self) -> Any:
        if self._filesystem_manager is None:
            from app.automation.filesystem_manager import FileSystemManager
            self._filesystem_manager = FileSystemManager()
        return self._filesystem_manager

    def list_dir(self, path: str = ".", recursive: bool = False, pattern: str | None = None) -> list[str]:
        return self.filesystem_manager.list_directory(path=path, recursive=recursive, pattern=pattern)

    def search(self, query: str, directory: str = ".", file_type: str | None = None) -> list[Any]:
        return self.filesystem_manager.search_files(query=query, directory=directory, file_type=file_type)

    def create_file(self, path: str, content: str = "") -> str:
        return self.filesystem_manager.create_file(path=path, content=content)

    def create_folder(self, path: str) -> str:
        return self.filesystem_manager.create_folder(path=path)

    def read_file(self, path: str, max_bytes: int | None = None) -> str:
        return self.filesystem_manager.read_file(path=path, max_bytes=max_bytes)

    def write_file(self, path: str, content: str, overwrite: bool = True) -> str:
        return self.filesystem_manager.write_file(path=path, content=content, overwrite=overwrite)

    def open_path(self, path: str) -> None:
        self.filesystem_manager.open_path(path=path)

    def copy(self, src: str, dst: str) -> str:
        return self.filesystem_manager.copy_path(src=src, dst=dst)

    def move(self, src: str, dst: str) -> str:
        return self.filesystem_manager.move_path(src=src, dst=dst)

    def rename(self, src: str, new_name: str) -> str:
        return self.filesystem_manager.rename_path(src=src, new_name=new_name)

    def delete(self, path: str) -> None:
        self.filesystem_manager.delete_path(path=path)

    def compress(self, sources: list[str] | str, dst_zip: str) -> str:
        return self.filesystem_manager.compress_archive(sources=sources, dst_zip=dst_zip)

    def extract(self, archive_path: str, dst_dir: str) -> str:
        return self.filesystem_manager.extract_archive(archive_path=archive_path, dst_dir=dst_dir)
