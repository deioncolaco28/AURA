"""
app/perception/scroll_handler.py

Scroll-aware perception and search across extended or paginated content.

Performs bounded observe-scroll-reobserve loops with termination checks
(target found, end-of-page reached, or maximum scroll limit reached).
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from app.intelligence.target_ranker import TargetRanker
from app.perception.target_query import TargetQuery
from app.perception.ui_element import UIElement

logger = logging.getLogger(__name__)


class ScrollPerceptionHandler:
    """
    Coordinates target search across scrollable views.
    """

    def __init__(
        self,
        max_scroll_attempts: int = 5,
        scroll_step_px: int = 400,
    ):
        self.max_scroll_attempts = max_scroll_attempts
        self.scroll_step_px = scroll_step_px

    def find_target_with_scrolling(
        self,
        observe_fn: Callable[[], Any],
        scroll_fn: Callable[[int], None],
        query: TargetQuery | str,
        ranker: TargetRanker | None = None,
        max_attempts: int | None = None,
    ) -> tuple[UIElement | None, int, str]:
        """
        Search for a target across visible and scrollable screen regions.

        Parameters
        ----------
        observe_fn : Callable returning a ScreenObservation or PerceptionResult
        scroll_fn : Callable accepting scroll delta (e.g. -400 for down)
        query : TargetQuery or string
        ranker : TargetRanker instance

        Returns
        -------
        tuple of (found_element, scrolls_performed, termination_reason)
        """
        if isinstance(query, str):
            from app.perception.target_query import parse_target_query
            target_query = parse_target_query(query)
        else:
            target_query = query

        ranker = ranker or TargetRanker()
        limit = max_attempts or self.max_scroll_attempts

        previous_signature: str | None = None
        scroll_count = 0

        for attempt in range(limit + 1):
            # 1. Observe current screen state
            observation = observe_fn()
            elements = getattr(observation, "elements", [])

            # 2. Check if target is visible and confident
            ranking = ranker.rank(elements, query=target_query)
            if ranking.found and ranking.best is not None:
                return ranking.best.element, scroll_count, "Target found."

            if attempt >= limit:
                break

            # 3. Check for end-of-page (screen signature unchanged after scroll)
            current_sig = getattr(observation, "screen_signature", None)
            if current_sig and previous_signature and current_sig == previous_signature:
                return None, scroll_count, "End of scrollable content reached."

            previous_signature = current_sig

            # 4. Perform bounded scroll
            try:
                scroll_fn(-self.scroll_step_px)
                scroll_count += 1
            except Exception as exc:
                return None, scroll_count, f"Scrolling failed: {exc}"

        return None, scroll_count, f"Target not found after {scroll_count} scroll attempts."
