"""Tests for ObservationDiffer — comparing before/after screen observations."""

import pytest

from app.core.observation import ScreenObservation
from app.core.observation_diff import ObservationDiff, ObservationDiffer
from app.perception.ui_element import UIElement


def make_element(eid, text, x=100, y=100, width=100, height=30):
    return UIElement(
        element_id=eid,
        element_type="button",
        text=text,
        x=x,
        y=y,
        width=width,
        height=height,
    )


def make_obs(
    texts=None,
    processes=None,
    window_title=None,
):
    elements = []
    screen_text = ""

    if texts:
        for i, t in enumerate(texts):
            elements.append(make_element(str(i), t))
        screen_text = "\n".join(texts)

    return ScreenObservation(
        screen_text=screen_text,
        elements=elements,
        processes=list(processes or []),
        window_title=window_title,
    )


# ---------------------------------------------------------------------------
# Basic no-change case
# ---------------------------------------------------------------------------


class TestNoChange:

    def test_identical_observations_no_diff(self):
        obs = make_obs(["Notepad", "Calculator"])
        differ = ObservationDiffer()
        diff = differ.compare(obs, obs)
        assert not diff.any_change


# ---------------------------------------------------------------------------
# Text differences
# ---------------------------------------------------------------------------


class TestTextDiff:

    def test_added_text(self):
        before = make_obs(["Notepad"])
        after = make_obs(["Notepad", "Calculator"])
        differ = ObservationDiffer()
        diff = differ.compare(before, after)
        assert any("calculator" in t for t in diff.added_text)

    def test_removed_text(self):
        before = make_obs(["Notepad", "Calculator"])
        after = make_obs(["Notepad"])
        differ = ObservationDiffer()
        diff = differ.compare(before, after)
        assert any("calculator" in t for t in diff.removed_text)

    def test_no_text_change(self):
        before = make_obs(["Notepad"])
        after = make_obs(["Notepad"])
        differ = ObservationDiffer()
        diff = differ.compare(before, after)
        assert not diff.added_text
        assert not diff.removed_text


# ---------------------------------------------------------------------------
# Element differences
# ---------------------------------------------------------------------------


class TestElementDiff:

    def test_added_element(self):
        before = make_obs(["Notepad"])
        after = make_obs(["Notepad", "Paint"])
        differ = ObservationDiffer()
        diff = differ.compare(before, after)
        assert any(
            "paint" in (e.text or "").lower()
            for e in diff.added_elements
        )

    def test_removed_element(self):
        before = make_obs(["Notepad", "Paint"])
        after = make_obs(["Notepad"])
        differ = ObservationDiffer()
        diff = differ.compare(before, after)
        assert any(
            "paint" in (e.text or "").lower()
            for e in diff.removed_elements
        )


# ---------------------------------------------------------------------------
# Process differences
# ---------------------------------------------------------------------------


class TestProcessDiff:

    def test_process_started(self):
        before = make_obs(processes=["explorer.exe"])
        after = make_obs(processes=["explorer.exe", "notepad.exe"])
        differ = ObservationDiffer()
        diff = differ.compare(before, after)
        assert "notepad.exe" in diff.processes_started
        assert diff.process_change

    def test_process_stopped(self):
        before = make_obs(processes=["explorer.exe", "notepad.exe"])
        after = make_obs(processes=["explorer.exe"])
        differ = ObservationDiffer()
        diff = differ.compare(before, after)
        assert "notepad.exe" in diff.processes_stopped
        assert diff.process_change

    def test_no_process_change(self):
        before = make_obs(processes=["explorer.exe"])
        after = make_obs(processes=["explorer.exe"])
        differ = ObservationDiffer()
        diff = differ.compare(before, after)
        assert not diff.process_change


# ---------------------------------------------------------------------------
# Window title change
# ---------------------------------------------------------------------------


class TestWindowTitleChange:

    def test_title_changed(self):
        before = make_obs(window_title="Desktop")
        after = make_obs(window_title="Notepad - Untitled")
        differ = ObservationDiffer()
        diff = differ.compare(before, after)
        assert diff.window_title_changed

    def test_title_unchanged(self):
        before = make_obs(window_title="Desktop")
        after = make_obs(window_title="Desktop")
        differ = ObservationDiffer()
        diff = differ.compare(before, after)
        assert not diff.window_title_changed


# ---------------------------------------------------------------------------
# Target appearance / disappearance
# ---------------------------------------------------------------------------


class TestTargetTracking:

    def test_target_appeared(self):
        before = make_obs([])
        after = make_obs(["Notepad"])
        differ = ObservationDiffer()
        diff = differ.compare(before, after, target="Notepad")
        assert diff.target_appeared
        assert not diff.target_disappeared

    def test_target_disappeared(self):
        before = make_obs(["Notepad"])
        after = make_obs([])
        differ = ObservationDiffer()
        diff = differ.compare(before, after, target="Notepad")
        assert diff.target_disappeared
        assert not diff.target_appeared

    def test_target_present_before_and_after_no_change(self):
        """
        Target present in both before and after → neither appeared
        nor disappeared.  This is the critical 'user did nothing' check.
        """
        before = make_obs(["Notepad"])
        after = make_obs(["Notepad"])
        differ = ObservationDiffer()
        diff = differ.compare(before, after, target="Notepad")
        assert not diff.target_appeared
        assert not diff.target_disappeared
        assert not diff.any_change

    def test_target_absent_before_and_after(self):
        before = make_obs(["Calculator"])
        after = make_obs(["Calculator"])
        differ = ObservationDiffer()
        diff = differ.compare(before, after, target="Notepad")
        assert not diff.target_appeared
        assert not diff.target_disappeared


# ---------------------------------------------------------------------------
# Noise robustness
# ---------------------------------------------------------------------------


class TestNoiseRobustness:

    def test_small_position_change_not_reported_as_changed(self):
        """Elements that move < noise threshold should not count as changed."""

        before_elem = UIElement(
            element_id="1",
            element_type="button",
            text="Notepad",
            x=100,
            y=100,
        )
        after_elem = UIElement(
            element_id="1",
            element_type="button",
            text="Notepad",
            x=105,   # only 5px change — within threshold
            y=102,
        )

        before = ScreenObservation(
            screen_text="Notepad",
            elements=[before_elem],
        )
        after = ScreenObservation(
            screen_text="Notepad",
            elements=[after_elem],
        )

        differ = ObservationDiffer(position_noise_threshold=15)
        diff = differ.compare(before, after)

        assert not diff.changed_elements
        assert not diff.any_change

    def test_large_position_change_reported(self):
        """Elements that move > noise threshold should be marked as changed."""

        before_elem = UIElement(
            element_id="1",
            element_type="button",
            text="Notepad",
            x=100,
            y=100,
        )
        after_elem = UIElement(
            element_id="1",
            element_type="button",
            text="Notepad",
            x=300,  # 200px change — well beyond threshold
            y=100,
        )

        before = ScreenObservation(
            screen_text="Notepad",
            elements=[before_elem],
        )
        after = ScreenObservation(
            screen_text="Notepad",
            elements=[after_elem],
        )

        differ = ObservationDiffer(position_noise_threshold=15)
        diff = differ.compare(before, after)

        assert diff.changed_elements
