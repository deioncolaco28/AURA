"""
app/automation/filesystem_manager.py

Robust, safe local filesystem manager for AURA.
Provides file/folder creation, modification, search, candidate ranking,
compression, and deletion with strict risk boundary enforcement.
"""

from __future__ import annotations

import difflib
import logging
import os
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config.constants import RiskLevel

logger = logging.getLogger(__name__)


@dataclass
class FileCandidate:
    """A scored file search result."""

    path: str
    filename: str
    score: float
    is_directory: bool = False
    file_size_bytes: int = 0
    modified_time: float = 0.0
    reason: str = ""
    extension: str = ""


@dataclass
class FileAmbiguityResult:
    """Ambiguity assessment when multiple files match a query."""

    is_ambiguous: bool
    top_candidates: list[FileCandidate] = field(default_factory=list)
    clarification_question: str = ""


class FileSystemManager:
    """
    Manages local filesystem operations safely using standard Python APIs.
    """

    AMBIGUITY_THRESHOLD = 0.15  # Score difference margin

    def __init__(self, base_directory: str | Path | None = None):
        self.base_directory = Path(base_directory or os.getcwd()).resolve()

    def _resolve_path(self, target_path: str | Path) -> Path:
        """Resolve a path relative to base directory or as absolute path."""
        p = Path(target_path)
        if not p.is_absolute():
            p = (self.base_directory / p).resolve()
        return p

    # ----------------------------------------------------------------------
    # Risk Classification
    # ----------------------------------------------------------------------

    @staticmethod
    def get_operation_risk(operation: str) -> str:
        """Return the risk level for a filesystem operation."""
        op = operation.lower().strip()
        if op in ("list", "search", "read", "metadata", "open"):
            return RiskLevel.LOW
        if op in ("create", "create_file", "create_folder", "rename", "move", "copy", "write"):
            return RiskLevel.MEDIUM
        if op in ("delete", "overwrite", "recursive_delete", "extract_overwrite"):
            return RiskLevel.HIGH
        return RiskLevel.MEDIUM

    # ----------------------------------------------------------------------
    # Create Operations
    # ----------------------------------------------------------------------

    def create_file(self, path: str | Path, content: str = "") -> str:
        """Create a new file with optional text content."""
        target = self._resolve_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return str(target)

    def create_folder(self, path: str | Path) -> str:
        """Create a new directory and any necessary parent directories."""
        target = self._resolve_path(path)
        target.mkdir(parents=True, exist_ok=True)
        return str(target)

    # ----------------------------------------------------------------------
    # Read & List Operations
    # ----------------------------------------------------------------------

    def read_file(self, path: str | Path, max_bytes: int | None = None) -> str:
        """Read text content from a file."""
        target = self._resolve_path(path)
        if not target.exists():
            raise FileNotFoundError(f"File not found: '{target}'")
        if not target.is_file():
            raise IsADirectoryError(f"Path is a directory, not a file: '{target}'")

        if max_bytes:
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                return f.read(max_bytes)
        return target.read_text(encoding="utf-8", errors="replace")

    def get_metadata(self, path: str | Path) -> dict[str, Any]:
        """Retrieve file or folder metadata."""
        target = self._resolve_path(path)
        if not target.exists():
            raise FileNotFoundError(f"Path does not exist: '{target}'")
        stat = target.stat()
        return {
            "path": str(target),
            "name": target.name,
            "is_file": target.is_file(),
            "is_dir": target.is_dir(),
            "size_bytes": stat.st_size,
            "created_time": stat.st_ctime,
            "modified_time": stat.st_mtime,
            "extension": target.suffix.lower(),
        }

    def list_directory(
        self,
        path: str | Path = ".",
        recursive: bool = False,
        pattern: str | None = None,
    ) -> list[str]:
        """List contents of a directory."""
        target = self._resolve_path(path)
        if not target.exists():
            raise FileNotFoundError(f"Directory not found: '{target}'")
        if not target.is_dir():
            raise NotADirectoryError(f"Path is not a directory: '{target}'")

        results: list[str] = []
        if recursive:
            iterator = target.rglob(pattern or "*")
        else:
            iterator = target.glob(pattern or "*")

        for item in iterator:
            results.append(str(item))

        return sorted(results)

    # ----------------------------------------------------------------------
    # Write, Copy, Move, Rename, Delete
    # ----------------------------------------------------------------------

    def write_file(self, path: str | Path, content: str, overwrite: bool = True) -> str:
        """Write content to a file."""
        target = self._resolve_path(path)
        if target.exists() and not overwrite:
            raise FileExistsError(f"File already exists and overwrite is False: '{target}'")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return str(target)

    def open_path(self, path: str | Path) -> None:
        """Open a file or directory in the default Windows application."""
        target = self._resolve_path(path)
        if not target.exists():
            raise FileNotFoundError(f"Path not found: '{target}'")
        try:
            os.startfile(str(target))
        except Exception:
            subprocess.Popen(["explorer.exe", str(target)], shell=False)

    def copy_path(self, src: str | Path, dst: str | Path) -> str:
        """Copy a file or directory to a destination."""
        s = self._resolve_path(src)
        d = self._resolve_path(dst)

        if not s.exists():
            raise FileNotFoundError(f"Source does not exist: '{s}'")

        if s.is_dir():
            if d.exists():
                d = d / s.name
            shutil.copytree(str(s), str(d), dirs_exist_ok=True)
        else:
            if d.is_dir():
                d = d / s.name
            else:
                d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(s), str(d))

        return str(d)

    def move_path(self, src: str | Path, dst: str | Path) -> str:
        """Move / rename a file or directory."""
        s = self._resolve_path(src)
        d = self._resolve_path(dst)

        if not s.exists():
            raise FileNotFoundError(f"Source does not exist: '{s}'")

        if d.is_dir() and not d.samefile(s.parent if s.parent.exists() else d):
            d = d / s.name
        else:
            d.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(s), str(d))
        return str(d)

    def rename_path(self, src: str | Path, new_name: str) -> str:
        """Rename a file or folder in place."""
        s = self._resolve_path(src)
        if not s.exists():
            raise FileNotFoundError(f"Source does not exist: '{s}'")

        target = s.parent / new_name
        s.rename(target)
        return str(target)

    def delete_path(self, path: str | Path) -> None:
        """Delete a file or directory."""
        target = self._resolve_path(path)
        if not target.exists():
            raise FileNotFoundError(f"Path does not exist: '{target}'")

        if target.is_dir():
            shutil.rmtree(str(target))
        else:
            target.unlink()

    # ----------------------------------------------------------------------
    # Compress & Extract
    # ----------------------------------------------------------------------

    def compress_archive(self, sources: list[str | Path] | str | Path, dst_zip: str | Path) -> str:
        """Compress file(s) or directory into a ZIP archive."""
        dest = self._resolve_path(dst_zip)
        dest.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(sources, (str, Path)):
            src_list = [self._resolve_path(sources)]
        else:
            src_list = [self._resolve_path(s) for s in sources]

        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zipf:
            for src in src_list:
                if not src.exists():
                    continue
                if src.is_file():
                    zipf.write(src, arcname=src.name)
                elif src.is_dir():
                    for root, _, files in os.walk(src):
                        for f in files:
                            full_p = Path(root) / f
                            rel_p = full_p.relative_to(src.parent)
                            zipf.write(full_p, arcname=str(rel_p))

        return str(dest)

    def extract_archive(self, archive_path: str | Path, dst_dir: str | Path) -> str:
        """Extract a ZIP archive to a target directory."""
        src = self._resolve_path(archive_path)
        dest = self._resolve_path(dst_dir)

        if not src.exists():
            raise FileNotFoundError(f"Archive not found: '{src}'")

        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(src, "r") as zipf:
            zipf.extractall(dest)

        return str(dest)

    # ----------------------------------------------------------------------
    # File Search & Candidate Ranking
    # ----------------------------------------------------------------------

    def search_files(
        self,
        query: str,
        directory: str | Path = ".",
        file_type: str | None = None,
        max_results: int = 10,
    ) -> list[FileCandidate]:
        """
        Search for files matching query with deterministic candidate ranking.
        """
        target_dir = self._resolve_path(directory)
        if not target_dir.exists():
            return []

        q_clean = query.strip().lower()
        candidates: list[FileCandidate] = []

        try:
            for root, _, files in os.walk(target_dir):
                for fname in files:
                    full_p = Path(root) / fname
                    ext = full_p.suffix.lower().lstrip(".")
                    fname_lower = fname.lower()

                    # Type filtering if specified (e.g. 'pdf', 'doc', 'image')
                    if file_type:
                        ft = file_type.lower().lstrip(".")
                        if ft == "image" and ext not in ("png", "jpg", "jpeg", "bmp", "gif"):
                            continue
                        elif ft == "document" and ext not in ("pdf", "docx", "doc", "txt", "md"):
                            continue
                        elif ft != ext and ft not in ("image", "document"):
                            continue

                    score = 0.0
                    reason_parts = []

                    # Exact name match
                    if q_clean == fname_lower or q_clean == full_p.stem.lower():
                        score = 1.0
                        reason_parts.append("exact filename match")
                    elif q_clean in fname_lower:
                        score = 0.8
                        reason_parts.append("substring match")
                    else:
                        # Fuzzy similarity ratio
                        sim = difflib.SequenceMatcher(None, q_clean, fname_lower).ratio()
                        if sim > 0.4:
                            score = sim * 0.75
                            reason_parts.append(f"fuzzy similarity {sim:.2f}")

                    if score > 0.0:
                        try:
                            stat = full_p.stat()
                            size = stat.st_size
                            mtime = stat.st_mtime
                        except Exception:
                            size = 0
                            mtime = 0.0

                        candidates.append(
                            FileCandidate(
                                path=str(full_p),
                                filename=fname,
                                score=round(score, 3),
                                is_directory=False,
                                file_size_bytes=size,
                                modified_time=mtime,
                                reason="; ".join(reason_parts),
                                extension=ext,
                            )
                        )
        except Exception as exc:
            logger.debug(f"Search directory error: {exc}")

        candidates.sort(key=lambda c: (c.score, c.modified_time), reverse=True)
        return candidates[:max_results]

    def check_ambiguity(self, query: str, candidates: list[FileCandidate]) -> FileAmbiguityResult:
        """Determine if search results are ambiguous and generate clarification."""
        if len(candidates) < 2:
            return FileAmbiguityResult(is_ambiguous=False, top_candidates=candidates)

        top1, top2 = candidates[0], candidates[1]
        if abs(top1.score - top2.score) <= self.AMBIGUITY_THRESHOLD:
            question = (
                f"I found multiple files matching '{query}': "
                f"1) '{top1.filename}' and 2) '{top2.filename}'. Which one would you like to use?"
            )
            return FileAmbiguityResult(
                is_ambiguous=True,
                top_candidates=[top1, top2],
                clarification_question=question,
            )

        return FileAmbiguityResult(is_ambiguous=False, top_candidates=[top1])
