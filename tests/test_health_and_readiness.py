"""
tests/test_health_and_readiness.py

Unit tests for AURA startup health and readiness validation.
"""

from unittest.mock import patch

from app.core.health import CapabilityStatus, HealthChecker, HealthReport


class TestHealthAndReadiness:
    def test_health_check_system_active(self):
        report = HealthChecker.check_system()
        assert isinstance(report, HealthReport)
        assert "runtime" in report.capabilities
        assert report.capabilities["runtime"].available is True
        assert "content_intelligence" in report.capabilities
        assert report.capabilities["content_intelligence"].available is True

    def test_summary_lines_formatting(self):
        report = HealthReport(
            overall_ready=True,
            capabilities={
                "voice": CapabilityStatus(name="voice", available=True, is_critical=False),
                "perception": CapabilityStatus(
                    name="perception", available=False, is_critical=False, details="No OCR"
                ),
            },
        )
        lines = report.summary_lines()
        assert len(lines) == 2
        assert "[+] Voice: Available" in lines[0]
        assert "[!] Perception: Unavailable (No OCR)" in lines[1]

    def test_optional_capability_degradation_does_not_abort_overall_readiness(self):
        with patch.object(HealthChecker, "_can_import", side_effect=lambda mod: mod != "speech_recognition"):
            report = HealthChecker.check_system()
            # Voice is optional, so missing speech_recognition should be a warning, not fatal
            assert report.capabilities["voice"].available is False
            assert len(report.warnings) > 0
