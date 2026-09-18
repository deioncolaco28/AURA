"""
app/intelligence/interaction_history.py

Simple learning-ready interaction history store.

Records the outcome of every target selection and action verification
so that the TargetRanker can use historical success rates to improve
future rankings.

The initial implementation is in-memory with optional JSON persistence.
No external database is required.

Data model
----------
Each recorded interaction contains:
    task : str
        Goal description.
    target : str
        Requested target label.
    element_id : str
        Selected element identifier.
    element_text : str
        Visible text of selected element.
    score : float
        Ranker score at time of selection.
    verification_result : str
        "success", "failure", or "unknown".
    timestamp : float
        Unix time.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Interaction record
# ---------------------------------------------------------------------------


@dataclass
class InteractionRecord:
    """One recorded target selection and its outcome."""

    task: str = ""
    target: str = ""
    element_id: str = ""
    element_text: str = ""
    score: float = 0.0
    verification_result: str = "unknown"  # "success" | "failure" | "unknown"
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.verification_result == "success"

    @property
    def failed(self) -> bool:
        return self.verification_result == "failure"


# ---------------------------------------------------------------------------
# InteractionHistory
# ---------------------------------------------------------------------------


class InteractionHistory:
    """
    Stores and queries the history of target selections and their outcomes.

    Usage
    -----
    ::

        history = InteractionHistory()

        history.record(
            task="open notepad",
            target="Notepad",
            element_id="1",
            element_text="Notepad",
            score=0.95,
            verification_result="success",
        )

        rate = history.success_rate("Notepad")  # → 1.0
    """

    def __init__(
        self,
        persistence_path: str | Path | None = None,
    ):
        self._records: list[InteractionRecord] = []
        self._persistence_path = (
            Path(persistence_path) if persistence_path else None
        )

        if self._persistence_path and self._persistence_path.exists():
            self._load()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(
        self,
        task: str = "",
        target: str = "",
        element_id: str = "",
        element_text: str = "",
        score: float = 0.0,
        verification_result: str = "unknown",
        metadata: dict[str, Any] | None = None,
    ) -> InteractionRecord:
        """
        Record the outcome of a target selection.

        Parameters
        ----------
        task : str
            The user's goal.
        target : str
            The requested target label.
        element_id : str
            The selected element's identifier.
        element_text : str
            The selected element's visible text.
        score : float
            The ranker score at selection time.
        verification_result : str
            "success", "failure", or "unknown".
        metadata : dict | None
            Optional extra context.

        Returns
        -------
        InteractionRecord
        """

        rec = InteractionRecord(
            task=task,
            target=target,
            element_id=element_id,
            element_text=element_text,
            score=score,
            verification_result=verification_result,
            metadata=metadata or {},
        )

        self._records.append(rec)

        if self._persistence_path:
            self._save()

        return rec

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def success_rate(
        self,
        target: str,
        element_text: str | None = None,
    ) -> float:
        """
        Return the historical success rate for a target label.

        Parameters
        ----------
        target : str
            Target label to query.
        element_text : str | None
            If provided, also match on element_text.

        Returns
        -------
        float in [0.0, 1.0], or 0.5 when no history exists.
        """

        target_norm = target.strip().lower()

        relevant = [
            r for r in self._records
            if (
                r.target.strip().lower() == target_norm
                or r.element_text.strip().lower() == target_norm
            )
            and r.verification_result != "unknown"
        ]

        if element_text:
            elem_norm = element_text.strip().lower()
            by_elem = [
                r for r in relevant
                if r.element_text.strip().lower() == elem_norm
            ]
            if by_elem:
                relevant = by_elem

        if not relevant:
            return 0.5  # neutral prior when no history

        successes = sum(1 for r in relevant if r.succeeded)

        return successes / len(relevant)

    def recent_records(
        self,
        limit: int = 20,
    ) -> list[InteractionRecord]:
        """Return the most recent interaction records."""

        return list(reversed(self._records[-limit:]))

    def all_records(self) -> list[InteractionRecord]:
        """Return all recorded interactions."""

        return list(self._records)

    def clear(self) -> None:
        """Clear all records (in-memory and persisted)."""

        self._records.clear()

        if self._persistence_path and self._persistence_path.exists():
            self._persistence_path.unlink()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        """Persist records to JSON."""

        if not self._persistence_path:
            return

        try:
            self._persistence_path.parent.mkdir(
                parents=True, exist_ok=True
            )

            data = [asdict(r) for r in self._records]

            with open(self._persistence_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

        except Exception as error:
            print(f"InteractionHistory: could not save: {error}")

    def _load(self) -> None:
        """Load records from JSON."""

        if not self._persistence_path:
            return

        try:
            with open(self._persistence_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for item in data:
                rec = InteractionRecord(**item)
                self._records.append(rec)

        except Exception as error:
            print(f"InteractionHistory: could not load: {error}")
