"""
app/core/observation_diff.py

Compares two ScreenObservation objects to identify meaningful
state transitions.

The diff is used by the tutoring verification system to determine
whether the user's action produced the expected result, and by the
autonomous recovery system to understand what changed on screen.

Key rules
---------
- Small coordinate noise (< POSITION_NOISE_THRESHOLD px) is ignored.
- Target presence alone is NOT considered proof of an action.
- Process changes are the strongest available evidence.
- Text additions/removals are secondary evidence.
- Pixel-level image differences are the weakest and are not used here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.perception.ui_element import UIElement


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

POSITION_NOISE_THRESHOLD = 15  # pixels — ignore movements smaller than this


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class ObservationDiff:
    """
    The difference between a before and after screen observation.

    Fields
    ------
    added_text : list[str]
        Text that appeared after the observation.
    removed_text : list[str]
        Text that disappeared after the observation.
    added_elements : list[UIElement]
        UI elements that appeared.
    removed_elements : list[UIElement]
        UI elements that disappeared.
    changed_elements : list[UIElement]
        UI elements whose position/size changed significantly.
    processes_started : list[str]
        Process names that appeared in the after observation.
    processes_stopped : list[str]
        Process names that disappeared in the after observation.
    window_title_changed : bool
        True when the foreground window title changed.
    target_appeared : bool
        True when a specific target was found in after but not before.
    target_disappeared : bool
        True when a specific target was found in before but not after.
    any_change : bool
        True when any meaningful difference was detected.
    metadata : dict
        Additional structured diff information.
    """

    added_text: list[str] = field(default_factory=list)
    removed_text: list[str] = field(default_factory=list)

    added_elements: list[UIElement] = field(default_factory=list)
    removed_elements: list[UIElement] = field(default_factory=list)
    changed_elements: list[UIElement] = field(default_factory=list)

    processes_started: list[str] = field(default_factory=list)
    processes_stopped: list[str] = field(default_factory=list)

    window_title_changed: bool = False
    foreground_app_changed: bool = False
    url_changed: bool = False

    target_appeared: bool = False
    target_disappeared: bool = False

    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def any_change(self) -> bool:
        """True when any meaningful difference was detected."""

        return bool(
            self.added_text
            or self.removed_text
            or self.added_elements
            or self.removed_elements
            or self.changed_elements
            or self.processes_started
            or self.processes_stopped
            or self.window_title_changed
            or self.foreground_app_changed
            or self.url_changed
            or self.target_appeared
            or self.target_disappeared
        )

    @property
    def screen_changed(self) -> bool:
        """Alias for any_change."""
        return self.any_change

    @property
    def has_meaningful_change(self) -> bool:
        """Alias for any_change."""
        return self.any_change

    @property
    def text_added(self) -> list[str]:
        """Alias for added_text."""
        return self.added_text

    @property
    def text_removed(self) -> list[str]:
        """Alias for removed_text."""
        return self.removed_text

    @property
    def elements_added(self) -> list[UIElement]:
        """Alias for added_elements."""
        return self.added_elements

    @property
    def elements_removed(self) -> list[UIElement]:
        """Alias for removed_elements."""
        return self.removed_elements

    @property
    def elements_moved(self) -> list[UIElement]:
        """Alias for changed_elements."""
        return self.changed_elements

    @property
    def foreground_changed(self) -> bool:
        """Alias for window_title_changed."""
        return self.window_title_changed

    @property
    def process_change(self) -> bool:
        """True when any process started or stopped."""

        return bool(
            self.processes_started
            or self.processes_stopped
        )


# ---------------------------------------------------------------------------
# Differ
# ---------------------------------------------------------------------------


class ObservationDiffer:
    """
    Compares two ScreenObservation objects and returns an ObservationDiff.

    Usage
    -----
    ::

        differ = ObservationDiffer()
        diff = differ.compare(before, after, target="Notepad")
    """

    def __init__(
        self,
        position_noise_threshold: int = POSITION_NOISE_THRESHOLD,
    ):
        self.position_noise_threshold = position_noise_threshold

    def compare(
        self,
        before,
        after,
        target: str | None = None,
    ) -> ObservationDiff:
        """
        Compare two ScreenObservation instances.

        Parameters
        ----------
        before : ScreenObservation
            Observation captured before the user acted.
        after : ScreenObservation
            Observation captured after the user acted.
        target : str | None
            Optional text target to check for appearance/disappearance.

        Returns
        -------
        ObservationDiff
        """

        diff = ObservationDiff()

        # ----------------------------------------------------------
        # Text differences
        # ----------------------------------------------------------
        diff.added_text, diff.removed_text = self._diff_text(
            before, after
        )

        # ----------------------------------------------------------
        # Element differences
        # ----------------------------------------------------------
        added, removed, changed = self._diff_elements(
            before, after
        )
        diff.added_elements = added
        diff.removed_elements = removed
        diff.changed_elements = changed

        # ----------------------------------------------------------
        # Process differences
        # ----------------------------------------------------------
        diff.processes_started, diff.processes_stopped = (
            self._diff_processes(before, after)
        )

        # ----------------------------------------------------------
        # Window title & Foreground App & URL
        # ----------------------------------------------------------
        diff.window_title_changed = self._title_changed(
            before, after
        )
        before_fg_ctx = getattr(before, "foreground_context", None)
        after_fg_ctx = getattr(after, "foreground_context", None)
        before_fg = str(getattr(before, "foreground_app", "") or (before_fg_ctx.app_name if before_fg_ctx else "") or "").strip().lower()
        after_fg = str(getattr(after, "foreground_app", "") or (after_fg_ctx.app_name if after_fg_ctx else "") or "").strip().lower()
        diff.foreground_app_changed = bool(before_fg and after_fg and before_fg != after_fg)

        before_url = str(getattr(before, "url", "") or "").strip().lower()
        after_url = str(getattr(after, "url", "") or "").strip().lower()
        diff.url_changed = bool(before_url and after_url and before_url != after_url)

        # ----------------------------------------------------------
        # Target appearance / disappearance
        # ----------------------------------------------------------
        if target:
            diff.target_appeared, diff.target_disappeared = (
                self._check_target(before, after, target)
            )

        # ----------------------------------------------------------
        # Metadata summary
        # ----------------------------------------------------------
        diff.metadata.update(
            {
                "added_text_count": len(diff.added_text),
                "removed_text_count": len(diff.removed_text),
                "added_elements": len(diff.added_elements),
                "removed_elements": len(diff.removed_elements),
                "processes_started": diff.processes_started,
                "processes_stopped": diff.processes_stopped,
                "target": target,
            }
        )

        return diff

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _element_texts(observation) -> set[str]:
        """Extract the set of visible text tokens from an observation."""

        texts: set[str] = set()

        for element in getattr(observation, "elements", []):
            text = str(getattr(element, "text", "") or "").strip()
            if text:
                texts.add(text.lower())

        raw_text = str(getattr(observation, "screen_text", "") or "")
        for token in raw_text.split("\n"):
            token = token.strip()
            if token:
                texts.add(token.lower())

        return texts

    def _diff_text(
        self,
        before,
        after,
    ) -> tuple[list[str], list[str]]:
        """Return (added, removed) text tokens."""

        before_texts = self._element_texts(before)
        after_texts = self._element_texts(after)

        added = sorted(after_texts - before_texts)
        removed = sorted(before_texts - after_texts)

        return added, removed

    def _diff_elements(
        self,
        before,
        after,
    ) -> tuple[list[UIElement], list[UIElement], list[UIElement]]:
        """
        Return (added, removed, changed) UIElement lists.

        Elements are matched by normalised text (case-insensitive).
        Position changes beyond the noise threshold are recorded as
        'changed'.
        """

        before_elements = list(
            getattr(before, "elements", [])
        )
        after_elements = list(
            getattr(after, "elements", [])
        )

        # Build lookup by normalised text.
        def _key(e) -> str:
            return str(
                getattr(e, "text", "") or ""
            ).strip().lower()

        before_by_text: dict[str, UIElement] = {}
        for e in before_elements:
            k = _key(e)
            if k:
                before_by_text[k] = e

        after_by_text: dict[str, UIElement] = {}
        for e in after_elements:
            k = _key(e)
            if k:
                after_by_text[k] = e

        added: list[UIElement] = []
        removed: list[UIElement] = []
        changed: list[UIElement] = []

        # Elements in after but not in before → added.
        for key, element in after_by_text.items():
            if key not in before_by_text:
                added.append(element)
            else:
                # Check for position change.
                bx, by = (
                    getattr(before_by_text[key], "x", 0),
                    getattr(before_by_text[key], "y", 0),
                )
                ax, ay = (
                    getattr(element, "x", 0),
                    getattr(element, "y", 0),
                )
                if (
                    abs(ax - bx) > self.position_noise_threshold
                    or abs(ay - by) > self.position_noise_threshold
                ):
                    changed.append(element)

        # Elements in before but not in after → removed.
        for key, element in before_by_text.items():
            if key not in after_by_text:
                removed.append(element)

        return added, removed, changed

    @staticmethod
    def _diff_processes(
        before,
        after,
    ) -> tuple[list[str], list[str]]:
        """Return (started, stopped) process name lists."""

        before_procs = set(
            str(p).lower()
            for p in getattr(before, "processes", [])
        )

        after_procs = set(
            str(p).lower()
            for p in getattr(after, "processes", [])
        )

        started = sorted(after_procs - before_procs)
        stopped = sorted(before_procs - after_procs)

        return started, stopped

    @staticmethod
    def _title_changed(before, after) -> bool:
        """True when the window title changed between observations."""

        before_title = str(
            getattr(before, "window_title", "") or ""
        ).strip().lower()

        after_title = str(
            getattr(after, "window_title", "") or ""
        ).strip().lower()

        if not before_title and not after_title:
            return False

        return before_title != after_title

    def _check_target(
        self,
        before,
        after,
        target: str,
    ) -> tuple[bool, bool]:
        """
        Return (appeared, disappeared) for a specific target text.

        'appeared' = not in before, is in after.
        'disappeared' = is in before, not in after.
        """

        target_normalized = target.strip().lower()

        before_texts = self._element_texts(before)
        after_texts = self._element_texts(after)

        # Check for partial match (the target word appears in any token).
        def _contains(texts: set[str]) -> bool:
            return any(
                target_normalized in t or t in target_normalized
                for t in texts
            )

        in_before = _contains(before_texts)
        in_after = _contains(after_texts)

        appeared = not in_before and in_after
        disappeared = in_before and not in_after

        return appeared, disappeared


def diff_observations(
    before,
    after,
    target: str | None = None,
) -> ObservationDiff:
    """Convenience helper to diff two ScreenObservation instances."""
    return ObservationDiffer().compare(before, after, target=target)
