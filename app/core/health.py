"""
app/core/health.py

Startup health and readiness validation for AURA.
Inspects runtime environments, optional capability backends,
and filesystem permissions without causing fatal aborts for non-critical features.
"""

from __future__ import annotations

import importlib
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CapabilityStatus:
    """Readiness status for an individual subsystem."""
    name: str
    available: bool
    is_critical: bool
    details: str = ""


@dataclass
class HealthReport:
    """Comprehensive readiness report across all AURA subsystems."""
    overall_ready: bool
    capabilities: dict[str, CapabilityStatus] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def summary_lines(self) -> list[str]:
        """Produce formatted status lines for startup console banner."""
        lines = []
        for name, cap in self.capabilities.items():
            symbol = "[+]" if cap.available else ("[-]" if cap.is_critical else "[!]")
            status_text = "Available" if cap.available else f"Unavailable ({cap.details})"
            lines.append(f"  {symbol} {name.capitalize()}: {status_text}")
        return lines


class HealthChecker:
    """Validates runtime prerequisites and module dependencies."""

    @classmethod
    def check_system(cls) -> HealthReport:
        capabilities: dict[str, CapabilityStatus] = {}
        warnings: list[str] = []
        errors: list[str] = []

        # 1. Python runtime
        py_ver = sys.version_info
        py_ok = py_ver.major == 3 and py_ver.minor >= 10
        capabilities["runtime"] = CapabilityStatus(
            name="runtime",
            available=py_ok,
            is_critical=True,
            details=f"Python {py_ver.major}.{py_ver.minor}.{py_ver.micro}",
        )
        if not py_ok:
            errors.append(f"Python 3.10+ required. Found {py_ver.major}.{py_ver.minor}")

        # 2. Voice (STT & TTS)
        stt_ok = cls._can_import("speech_recognition")
        tts_ok = cls._can_import("pyttsx3")
        voice_ok = stt_ok and tts_ok
        capabilities["voice"] = CapabilityStatus(
            name="voice",
            available=voice_ok,
            is_critical=False,
            details="STT/TTS engines loaded" if voice_ok else "Microphone/TTS optional",
        )
        if not voice_ok:
            warnings.append("Voice features unavailable. Falling back to text mode.")

        # 3. Desktop Automation
        auto_ok = cls._can_import("pyautogui")
        capabilities["desktop_automation"] = CapabilityStatus(
            name="desktop_automation",
            available=auto_ok,
            is_critical=True,
            details="PyAutoGUI loaded" if auto_ok else "PyAutoGUI missing",
        )
        if not auto_ok:
            errors.append("Desktop automation backend is missing.")

        # 4. Perception / OCR
        ocr_ok = cls._can_import("pytesseract")
        capabilities["perception"] = CapabilityStatus(
            name="perception",
            available=ocr_ok,
            is_critical=False,
            details="Tesseract/OCR loaded" if ocr_ok else "OCR fallback to DOM/Accessibility",
        )

        # 5. Content Intelligence Libraries
        pypdf_ok = cls._can_import("pypdf")
        docx_ok = cls._can_import("docx")
        xlsx_ok = cls._can_import("openpyxl")
        pptx_ok = cls._can_import("pptx")
        bs4_ok = cls._can_import("bs4")
        content_ok = pypdf_ok and docx_ok and xlsx_ok and pptx_ok and bs4_ok

        capabilities["content_intelligence"] = CapabilityStatus(
            name="content_intelligence",
            available=content_ok,
            is_critical=True,
            details="PDF, DOCX, XLSX, PPTX, HTML adapters active",
        )
        if not content_ok:
            errors.append("One or more content intelligence packages missing.")

        # 6. Filesystem Write Access
        fs_ok = cls._check_fs_permissions()
        capabilities["filesystem"] = CapabilityStatus(
            name="filesystem",
            available=fs_ok,
            is_critical=True,
            details="Read/Write permissions verified",
        )
        if not fs_ok:
            errors.append("Log/Data directories are not writable.")

        overall_ready = len(errors) == 0

        return HealthReport(
            overall_ready=overall_ready,
            capabilities=capabilities,
            warnings=warnings,
            errors=errors,
        )

    @staticmethod
    def _can_import(module_name: str) -> bool:
        try:
            importlib.import_module(module_name)
            return True
        except ImportError:
            return False

    @staticmethod
    def _check_fs_permissions() -> bool:
        try:
            test_dir = Path("data/temp")
            test_dir.mkdir(parents=True, exist_ok=True)
            test_file = test_dir / ".health_check_tmp"
            test_file.write_text("health_check_ok", encoding="utf-8")
            if test_file.exists():
                test_file.unlink()
            return True
        except Exception:
            return False
