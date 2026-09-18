"""
app/core/performance.py

Lightweight performance timer and context manager for AURA.
Allows precise duration measurements without runtime overhead.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Generator


class PerformanceTimer:
    """High-resolution elapsed time tracker."""

    def __init__(self):
        self._start_time: float = 0.0
        self._end_time: float = 0.0
        self._elapsed_ms: float = 0.0

    def start(self) -> None:
        self._start_time = time.perf_counter()

    def stop(self) -> float:
        self._end_time = time.perf_counter()
        self._elapsed_ms = (self._end_time - self._start_time) * 1000.0
        return self._elapsed_ms

    @property
    def elapsed_ms(self) -> float:
        if self._end_time > 0:
            return self._elapsed_ms
        return (time.perf_counter() - self._start_time) * 1000.0


@contextmanager
def measure_time() -> Generator[dict[str, float], None, None]:
    """
    Context manager yielding a dict that receives elapsed_ms upon exit.

    Usage:
        with measure_time() as timing:
            do_work()
        print(timing["elapsed_ms"])
    """
    res = {"elapsed_ms": 0.0}
    start = time.perf_counter()
    try:
        yield res
    finally:
        res["elapsed_ms"] = (time.perf_counter() - start) * 1000.0
