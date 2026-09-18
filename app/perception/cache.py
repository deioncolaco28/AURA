"""
app/perception/cache.py

Lightweight perception result caching to avoid redundant expensive OCR / VLM
operations when the screen has not changed.

Automatically invalidated on actions, scrolls, navigation, and window changes.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

from app.perception.perception_result import PerceptionResult


class PerceptionCache:
    """
    Perception result cache keyed by visual & context fingerprints.
    """

    def __init__(self, ttl_seconds: float = 2.0, enabled: bool = True):
        self.ttl_seconds = ttl_seconds
        self.enabled = enabled
        self._cache: dict[str, tuple[float, PerceptionResult]] = {}
        self._last_signature: str | None = None

    def compute_signature(
        self,
        image: Any,
        foreground_app: str | None = None,
        window_title: str | None = None,
    ) -> str:
        """
        Compute a fast, deterministic fingerprint of the current screen and window state.
        """
        if image is None:
            raw = f"none:{foreground_app or ''}:{window_title or ''}"
            return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

        # Use image size, mode, sample pixel bytes for fast perceptual hashing
        img_info = ""
        size = getattr(image, "size", None)
        mode = getattr(image, "mode", None)
        if size:
            img_info = f"{size[0]}x{size[1]}_{mode}"

        # Fast sample of center and corner pixels if PIL Image
        sample_bytes = b""
        try:
            if hasattr(image, "tobytes") and callable(image.tobytes):
                res = image.tobytes()
                if isinstance(res, (bytes, bytearray)):
                    sample_bytes = bytes(res[:128])
            elif hasattr(image, "resize"):
                small = image.resize((16, 16))
                if hasattr(small, "tobytes") and callable(small.tobytes):
                    res = small.tobytes()
                    if isinstance(res, (bytes, bytearray)):
                        sample_bytes = bytes(res)
        except Exception:
            sample_bytes = b""

        if not isinstance(sample_bytes, (bytes, bytearray)):
            sample_bytes = b""

        raw_data = sample_bytes + f":{img_info}:{foreground_app or ''}:{window_title or ''}".encode("utf-8")
        return hashlib.sha256(raw_data).hexdigest()[:16]

    def get(self, signature: str) -> PerceptionResult | None:
        """Retrieve cached result if signature matches and TTL has not expired."""
        if not self.enabled or signature not in self._cache:
            return None

        cached_time, result = self._cache[signature]
        if time.time() - cached_time > self.ttl_seconds:
            del self._cache[signature]
            return None

        return result

    def set(self, signature: str, result: PerceptionResult) -> None:
        """Store perception result under the given signature."""
        if not self.enabled:
            return
        self._cache[signature] = (time.time(), result)
        self._last_signature = signature

    def invalidate(self, reason: str | None = None) -> None:
        """Explicitly clear the entire cache."""
        self._cache.clear()
        self._last_signature = None

    def on_action_executed(self) -> None:
        """Invalidate cache after any desktop or browser action."""
        self.invalidate()

    def on_scroll(self) -> None:
        """Invalidate cache after scroll events."""
        self.invalidate()

    def on_navigation(self) -> None:
        """Invalidate cache after browser navigation."""
        self.invalidate()
