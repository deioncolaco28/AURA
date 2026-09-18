"""
app/config/config.py

Centralized typed configuration system for AURA.
Provides modular sub-configurations with safe defaults, validation,
and environment variable overrides.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class VoiceConfig:
    """Configuration for Speech-to-Text and Text-to-Speech."""
    voice_enabled: bool = True
    stt_model: str = "google"
    stt_energy_threshold: int = 300
    stt_dynamic_energy: bool = True
    stt_pause_threshold: float = 0.8
    tts_rate: int = 180
    tts_volume: float = 1.0
    greeting_message: str = (
        "Hello! I'm AURA. I'm ready to help. Please tell me what you'd like me to do."
    )


@dataclass
class ExecutionConfig:
    """Configuration for action execution, timeouts, and retries."""
    default_mode: str = "DO_IT_FOR_ME"
    max_retries: int = 3
    max_replans: int = 2
    polling_timeout_sec: float = 5.0
    task_timeout_sec: float = 60.0
    screenshot_dir: str = "data/screenshots"
    log_dir: str = "data/logs"
    temp_dir: str = "data/temp"
    benchmark_dir: str = "data/benchmarks"


@dataclass
class PerceptionConfig:
    """Configuration for UI perception, OCR, and spatial reasoning."""
    cache_ttl_sec: float = 1.0
    ocr_confidence_threshold: float = 0.5
    vlm_enabled: bool = False
    spatial_reasoning_enabled: bool = True
    scroll_search_max_steps: int = 5
    max_cached_elements: int = 200


@dataclass
class ContentConfig:
    """Configuration for document and web content intelligence."""
    max_cache_entries: int = 50
    pdf_ocr_fallback: bool = True
    table_extraction_enabled: bool = True
    grounding_threshold: float = 0.6
    max_summary_sentences: int = 5
    max_doc_file_size_mb: int = 50


@dataclass
class SafetyConfig:
    """Configuration for risk assessment, safety policies, and confirmation."""
    confirmation_policy: str = "high_risk_only"  # "always" | "high_risk_only" | "never"
    min_confidence_to_act: float = 0.5
    unrestricted_shell_allowed: bool = False
    block_macro_execution: bool = True
    blocked_directories: list[str] = field(
        default_factory=lambda: [
            "C:\\Windows",
            "C:\\Windows\\System32",
            "C:\\Program Files",
            "C:\\Program Files (x86)",
        ]
    )
    safe_working_directories: list[str] = field(
        default_factory=lambda: [
            str(Path.home() / "Desktop"),
            str(Path.home() / "Documents"),
            str(Path.home() / "Downloads"),
        ]
    )


@dataclass
class LoggingConfig:
    """Configuration for structured logging and task tracing."""
    level: str = "INFO"
    structured_json: bool = True
    record_traces: bool = True
    verbose_console: bool = False
    log_file_name: str = "aura.log"
    trace_file_name: str = "aura_traces.jsonl"


@dataclass
class EvaluationConfig:
    """Configuration for research evaluation and benchmarks."""
    benchmark_output_dir: str = "data/evaluation"
    deterministic_mode: bool = True
    record_metrics: bool = True
    include_system_info: bool = True


@dataclass
class AURAConfig:
    """Master configuration container for AURA."""
    app_name: str = "AURA"
    full_name: str = "Automated User Response Assistant"
    version: str = "1.0.0"
    environment: str = os.getenv("APP_ENV", "development")

    voice: VoiceConfig = field(default_factory=VoiceConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    perception: PerceptionConfig = field(default_factory=PerceptionConfig)
    content: ContentConfig = field(default_factory=ContentConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    evaluation: EvaluationConfig = field(default_factory=EvaluationConfig)

    @classmethod
    def load_from_env(cls) -> AURAConfig:
        """Create configuration overridden with environment variables."""
        cfg = cls()

        env_name = os.getenv("APP_ENV")
        if env_name:
            cfg.environment = env_name

        mode = os.getenv("AURA_DEFAULT_MODE")
        if mode:
            cfg.execution.default_mode = mode

        max_retries = os.getenv("AURA_MAX_RETRIES")
        if max_retries and max_retries.isdigit():
            cfg.execution.max_retries = int(max_retries)

        voice_en = os.getenv("AURA_VOICE_ENABLED")
        if voice_en is not None:
            cfg.voice.voice_enabled = voice_en.lower() in ("true", "1", "yes")

        log_lvl = os.getenv("AURA_LOG_LEVEL")
        if log_lvl:
            cfg.logging.level = log_lvl.upper()

        conf_pol = os.getenv("AURA_CONFIRMATION_POLICY")
        if conf_pol:
            cfg.safety.confirmation_policy = conf_pol

        return cfg


# Global singleton default config
config = AURAConfig.load_from_env()
