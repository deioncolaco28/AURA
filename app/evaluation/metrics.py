"""
app/evaluation/metrics.py

Formal evaluation metrics calculation engine for AURA.
Calculates strictly defined quantitative rates and aggregations for research papers and benchmarks.
"""

from __future__ import annotations

from typing import Sequence

from app.evaluation.models import MetricReport, ScenarioResult


class MetricCalculator:
    """
    Computes formal quantitative metrics from benchmark ScenarioResults.
    """

    @classmethod
    def calculate(cls, results: Sequence[ScenarioResult]) -> MetricReport:
        if not results:
            return MetricReport()

        total = len(results)
        passed = sum(1 for r in results if r.status == "PASSED")
        failed = sum(1 for r in results if r.status == "FAILED")

        # 1. Task Success Rate = verified passed / total attempted
        task_success_rate = passed / total if total > 0 else 0.0

        # 2. Verification Accuracy = verification_passed / total
        verification_passed_count = sum(1 for r in results if r.verification_passed)
        verification_accuracy = verification_passed_count / total if total > 0 else 0.0

        # 3. Target Grounding Accuracy = grounding_accurate / total
        grounding_count = sum(1 for r in results if r.grounding_accurate)
        target_grounding_accuracy = grounding_count / total if total > 0 else 0.0

        # 4. Recovery Success Rate = successful recoveries / total recovery attempts
        recovery_attempts = [r for r in results if r.recovery_occurred]
        recovery_successes = sum(1 for r in recovery_attempts if r.recovery_success)
        recovery_success_rate = (
            recovery_successes / len(recovery_attempts) if recovery_attempts else 1.0
        )

        # 5. Average Attempts per Task
        total_attempts = sum(r.attempts for r in results)
        avg_attempts = total_attempts / total if total > 0 else 1.0

        # 6. Average Completion Time (ms)
        total_duration = sum(r.duration_ms for r in results)
        avg_duration = total_duration / total if total > 0 else 0.0

        # 7. Replanning Rate = scenarios with replan > 0 / total
        replanned = sum(1 for r in results if r.replan_count > 0)
        replanning_rate = replanned / total if total > 0 else 0.0

        # 8. User Intervention Rate
        intervened = sum(1 for r in results if r.user_intervention)
        user_intervention_rate = intervened / total if total > 0 else 0.0

        # 9. Tutoring Completion Rate
        tutoring_scenarios = [r for r in results if r.category == "tutoring"]
        tutoring_completed = sum(1 for r in tutoring_scenarios if r.tutoring_completed)
        tutoring_rate = (
            tutoring_completed / len(tutoring_scenarios) if tutoring_scenarios else 1.0
        )

        # 10. Content Extraction Success Rate
        content_scenarios = [r for r in results if r.category == "content"]
        content_extracted = sum(
            1 for r in content_scenarios if r.content_extraction_success
        )
        content_ext_rate = (
            content_extracted / len(content_scenarios) if content_scenarios else 1.0
        )

        # 11. Content QA Grounding Rate
        content_qa_grounded = sum(
            1 for r in content_scenarios if r.content_qa_grounded
        )
        content_qa_rate = (
            content_qa_grounded / len(content_scenarios) if content_scenarios else 1.0
        )

        # Category Breakdown
        categories: dict[str, list[ScenarioResult]] = {}
        for r in results:
            categories.setdefault(r.category, []).append(r)

        category_breakdown: dict[str, dict] = {}
        for cat, cat_res in categories.items():
            cat_total = len(cat_res)
            cat_passed = sum(1 for cr in cat_res if cr.status == "PASSED")
            category_breakdown[cat] = {
                "total": cat_total,
                "passed": cat_passed,
                "success_rate": round(cat_passed / cat_total, 3) if cat_total > 0 else 0.0,
                "avg_duration_ms": round(sum(cr.duration_ms for cr in cat_res) / cat_total, 1) if cat_total > 0 else 0.0,
            }

        return MetricReport(
            total_scenarios=total,
            passed_scenarios=passed,
            failed_scenarios=failed,
            task_success_rate=round(task_success_rate, 4),
            verification_accuracy=round(verification_accuracy, 4),
            target_grounding_accuracy=round(target_grounding_accuracy, 4),
            recovery_success_rate=round(recovery_success_rate, 4),
            average_attempts_per_task=round(avg_attempts, 2),
            average_duration_ms=round(avg_duration, 1),
            replanning_rate=round(replanning_rate, 4),
            user_intervention_rate=round(user_intervention_rate, 4),
            tutoring_completion_rate=round(tutoring_rate, 4),
            content_extraction_success_rate=round(content_ext_rate, 4),
            content_qa_grounding_rate=round(content_qa_rate, 4),
            category_breakdown=category_breakdown,
        )
