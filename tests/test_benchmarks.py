"""
tests/test_benchmarks.py

Unit tests for AURA Benchmark runner, Scenario definitions, and Metric calculations.
"""

from tempfile import TemporaryDirectory

from app.evaluation.benchmark_runner import BenchmarkRunner
from app.evaluation.metrics import MetricCalculator
from app.evaluation.models import (
    BenchmarkCategory,
    BenchmarkScenario,
    MetricReport,
    ScenarioResult,
)
from app.evaluation.scenarios import get_standard_scenarios


class TestBenchmarksAndMetrics:
    def test_standard_scenarios_coverage(self):
        scenarios = get_standard_scenarios()
        assert len(scenarios) >= 10
        categories = {sc.category for sc in scenarios}
        assert BenchmarkCategory.DESKTOP in categories
        assert BenchmarkCategory.BROWSER in categories
        assert BenchmarkCategory.FILESYSTEM in categories
        assert BenchmarkCategory.PERCEPTION in categories
        assert BenchmarkCategory.AGENT in categories
        assert BenchmarkCategory.CONTENT in categories
        assert BenchmarkCategory.TUTORING in categories

    def test_metric_calculation_formulas(self):
        results = [
            ScenarioResult(
                scenario_id="SC-1",
                category="desktop",
                status="PASSED",
                duration_ms=100.0,
                attempts=1,
                verification_passed=True,
                grounding_accurate=True,
                recovery_occurred=False,
            ),
            ScenarioResult(
                scenario_id="SC-2",
                category="content",
                status="PASSED",
                duration_ms=200.0,
                attempts=2,
                verification_passed=True,
                grounding_accurate=True,
                recovery_occurred=True,
                recovery_success=True,
                replan_count=1,
                content_extraction_success=True,
                content_qa_grounded=True,
            ),
            ScenarioResult(
                scenario_id="SC-3",
                category="tutoring",
                status="PASSED",
                duration_ms=300.0,
                attempts=1,
                verification_passed=True,
                grounding_accurate=True,
                recovery_occurred=False,
                tutoring_completed=True,
            ),
        ]

        metrics = MetricCalculator.calculate(results)
        assert isinstance(metrics, MetricReport)
        assert metrics.total_scenarios == 3
        assert metrics.passed_scenarios == 3
        assert metrics.task_success_rate == 1.0
        assert metrics.verification_accuracy == 1.0
        assert metrics.target_grounding_accuracy == 1.0
        assert metrics.recovery_success_rate == 1.0
        assert metrics.average_attempts_per_task == round((1 + 2 + 1) / 3, 2)
        assert metrics.average_duration_ms == 200.0
        assert metrics.replanning_rate == round(1 / 3, 4)
        assert metrics.tutoring_completion_rate == 1.0
        assert metrics.content_extraction_success_rate == 1.0

    def test_benchmark_runner_deterministic_execution(self):
        with TemporaryDirectory() as tmp_dir:
            runner = BenchmarkRunner(output_dir=tmp_dir)
            result = runner.run_all(deterministic=True)

            assert result.metrics.total_scenarios >= 10
            assert result.metrics.task_success_rate == 1.0
            assert len(result.scenario_results) >= 10

            # Check markdown generation
            md = result.metrics.to_markdown_table()
            assert "Task Success Rate" in md
            assert "Verification Accuracy" in md
