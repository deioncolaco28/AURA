"""
tests/test_config.py

Unit tests for AURA's centralized typed configuration system.
"""

import os
from unittest.mock import patch

from app.config import (
    AURAConfig,
    ContentConfig,
    EvaluationConfig,
    ExecutionConfig,
    LoggingConfig,
    PerceptionConfig,
    SafetyConfig,
    VoiceConfig,
    config,
    settings,
)


class TestAURAConfig:
    def test_default_configuration_structure(self):
        cfg = AURAConfig()
        assert cfg.app_name == "AURA"
        assert isinstance(cfg.voice, VoiceConfig)
        assert isinstance(cfg.execution, ExecutionConfig)
        assert isinstance(cfg.perception, PerceptionConfig)
        assert isinstance(cfg.content, ContentConfig)
        assert isinstance(cfg.safety, SafetyConfig)
        assert isinstance(cfg.logging, LoggingConfig)
        assert isinstance(cfg.evaluation, EvaluationConfig)

    def test_default_values(self):
        cfg = AURAConfig()
        assert cfg.execution.default_mode == "DO_IT_FOR_ME"
        assert cfg.execution.max_retries == 3
        assert cfg.safety.confirmation_policy == "high_risk_only"
        assert cfg.safety.unrestricted_shell_allowed is False
        assert cfg.content.max_cache_entries == 50
        assert cfg.perception.cache_ttl_sec == 1.0

    def test_env_variable_overrides(self):
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "AURA_DEFAULT_MODE": "SHOW_ME_HOW",
                "AURA_MAX_RETRIES": "5",
                "AURA_VOICE_ENABLED": "false",
                "AURA_LOG_LEVEL": "DEBUG",
                "AURA_CONFIRMATION_POLICY": "always",
            },
        ):
            loaded = AURAConfig.load_from_env()
            assert loaded.environment == "production"
            assert loaded.execution.default_mode == "SHOW_ME_HOW"
            assert loaded.execution.max_retries == 5
            assert loaded.voice.voice_enabled is False
            assert loaded.logging.level == "DEBUG"
            assert loaded.safety.confirmation_policy == "always"

    def test_backward_compatibility_with_settings(self):
        assert settings.app_name == "AURA"
        assert settings.default_mode == "DO_IT_FOR_ME"
        assert hasattr(settings, "screenshot_directory")
