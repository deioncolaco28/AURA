"""
app/perception/perception_manager.py

Coordinates multi-source perception (Accessibility, DOM, OCR, VLM),
performs fusion and normalization, manages perception caching,
and constructs the canonical UIElementGraph.
"""

from __future__ import annotations

import logging
from typing import Any

from app.perception.accessibility import AccessibilityProvider
from app.perception.cache import PerceptionCache
from app.perception.config import PerceptionConfig
from app.perception.ocr import OCR
from app.perception.perception_result import PerceptionResult
from app.perception.ui_element import UIElement, generate_stable_id
from app.perception.ui_graph import UIElementGraph
from app.perception.vlm import VLM

logger = logging.getLogger(__name__)


class PerceptionManager:
    """
    Coordinates Accessibility, OCR, and VLM perception into a unified UI model.

    Pipeline:
        Screenshot + Window Context
            ↓
        Cache Check
            ↓
        Accessibility / DOM Capture
            ↓
        OCR Capture
            ↓
        VLM Capture
            ↓
        Multi-source Fusion & Deduplication
            ↓
        UIElementGraph Construction
            ↓
        PerceptionResult
    """

    def __init__(
        self,
        ocr: OCR | None = None,
        vlm: VLM | None = None,
        accessibility_provider: AccessibilityProvider | None = None,
        cache: PerceptionCache | None = None,
        config: PerceptionConfig | None = None,
    ):
        self.ocr = ocr
        self.vlm = vlm
        self.accessibility_provider = accessibility_provider
        self.config = config or PerceptionConfig()
        self.cache = cache or (PerceptionCache(
            ttl_seconds=self.config.cache_ttl_seconds,
            enabled=self.config.cache_enabled,
        ) if self.config.cache_enabled else None)

    @property
    def FUSION_DISTANCE_THRESHOLD(self) -> int:
        return self.config.fusion_distance_threshold

    @property
    def TEXT_SIMILARITY_THRESHOLD(self) -> float:
        return self.config.text_similarity_threshold

    @property
    def IOU_THRESHOLD(self) -> float:
        return self.config.fusion_iou_threshold

    def analyze(
        self,
        image: Any,
        instruction: str | None = None,
        foreground_app: str | None = None,
        window_title: str | None = None,
        use_cache: bool = True,
    ) -> PerceptionResult:
        """
        Analyze the current screen using all available perception sources.
        """
        # ---------------------------------------------------------
        # Cache lookup
        # ---------------------------------------------------------
        cache_sig = ""
        if use_cache and self.cache is not None and self.cache.enabled:
            cache_sig = self.cache.compute_signature(
                image,
                foreground_app=foreground_app,
                window_title=window_title,
            )
            cached = self.cache.get(cache_sig)
            if cached is not None:
                return cached

        elements: list[UIElement] = []
        sources_used: list[str] = []
        screen_description = ""

        # ---------------------------------------------------------
        # 1. Structured Accessibility / DOM perception
        # ---------------------------------------------------------
        if self.accessibility_provider is not None and self.accessibility_provider.is_available():
            try:
                acc_elements = self.accessibility_provider.capture()
                if acc_elements:
                    elements.extend(acc_elements)
                    sources_used.append("ACCESSIBILITY")
            except Exception as exc:
                logger.debug(f"Accessibility capture error: {exc}")

        # ---------------------------------------------------------
        # 2. OCR perception
        # ---------------------------------------------------------
        if self.ocr is not None and image is not None:
            try:
                ocr_elements = self._run_ocr(image, app_name=foreground_app, window_title=window_title)
                elements.extend(ocr_elements)
                sources_used.append("OCR")
            except Exception as exc:
                logger.debug(f"OCR capture error: {exc}")

        # ---------------------------------------------------------
        # 3. VLM perception (if configured)
        # ---------------------------------------------------------
        if self.vlm is not None and image is not None:
            try:
                vlm_result = self.vlm.analyze(image, instruction=instruction)
                vlm_elements = self._convert_vlm_elements(
                    vlm_result.elements,
                    app_name=foreground_app,
                    window_title=window_title,
                )
                elements.extend(vlm_elements)
                sources_used.append("VLM")
                screen_description = vlm_result.description
            except Exception as exc:
                logger.debug(f"VLM capture error: {exc}")

        # ---------------------------------------------------------
        # 4. Multi-Source Fusion & Deduplication
        # ---------------------------------------------------------
        fused_elements = self._fuse_elements(elements)

        # ---------------------------------------------------------
        # 5. UI Element Graph Construction
        # ---------------------------------------------------------
        ui_graph = UIElementGraph.build_from_elements(fused_elements)

        # Calculate overall confidence
        overall_conf = 0.0
        if fused_elements:
            overall_conf = sum(e.confidence for e in fused_elements) / len(fused_elements)

        result = PerceptionResult(
            elements=fused_elements,
            screen_description=screen_description,
            sources_used=sources_used,
            screenshot=image,
            ui_graph=ui_graph,
            overall_confidence=round(overall_conf, 3),
            metadata={
                "raw_element_count": len(elements),
                "fused_element_count": len(fused_elements),
                "fusion_applied": len(elements) != len(fused_elements),
                "instruction": instruction,
                "foreground_app": foreground_app,
                "window_title": window_title,
                "ocr_enabled": self.ocr is not None,
                "vlm_enabled": self.vlm is not None,
                "accessibility_enabled": self.accessibility_provider is not None and self.accessibility_provider.is_available(),
            },
        )

        # Cache valid result
        if use_cache and self.cache is not None and self.cache.enabled and cache_sig:
            self.cache.set(cache_sig, result)

        return result

    # Alias for analyze
    perceive = analyze

    # =============================================================
    # OCR
    # =============================================================

    def _run_ocr(
        self,
        image: Any,
        app_name: str | None = None,
        window_title: str | None = None,
    ) -> list[UIElement]:
        results = self.ocr.detect_text(image)
        elements: list[UIElement] = []

        for index, element in enumerate(results):
            raw_text = element.text
            conf = self._normalize_confidence(element.confidence)
            if conf < self.config.minimum_ocr_confidence:
                continue

            elements.append(
                UIElement(
                    element_id=f"ocr-{index}",
                    element_type="text",
                    text=raw_text,
                    x=element.x,
                    y=element.y,
                    width=element.width,
                    height=element.height,
                    confidence=conf,
                    source="OCR",
                    app_name=app_name,
                    window_title=window_title,
                )
            )

        return elements

    # =============================================================
    # VLM
    # =============================================================

    def _convert_vlm_elements(
        self,
        vlm_elements: list[Any],
        app_name: str | None = None,
        window_title: str | None = None,
    ) -> list[UIElement]:
        elements: list[UIElement] = []

        for index, element in enumerate(vlm_elements):
            element_id = getattr(element, "element_id", None) or f"vlm-{index}"
            conf = self._normalize_confidence(getattr(element, "confidence", 1.0))
            if conf < self.config.minimum_vlm_confidence:
                continue

            elements.append(
                UIElement(
                    element_id=element_id,
                    element_type=getattr(element, "element_type", "element"),
                    text=getattr(element, "text", None),
                    description=getattr(element, "description", None),
                    x=getattr(element, "x", 0),
                    y=getattr(element, "y", 0),
                    width=getattr(element, "width", 0),
                    height=getattr(element, "height", 0),
                    confidence=conf,
                    source="VLM",
                    attributes=dict(getattr(element, "attributes", {})),
                    app_name=app_name,
                    window_title=window_title,
                )
            )

        return elements

    # =============================================================
    # FUSION
    # =============================================================

    def _fuse_elements(
        self,
        elements: list[UIElement],
    ) -> list[UIElement]:
        """
        Merge complementary elements referring to the same visual UI component.
        """
        fused: list[UIElement] = []

        for element in elements:
            duplicate_index = self._find_duplicate(element, fused)

            if duplicate_index is None:
                fused.append(element)
                continue

            fused[duplicate_index] = self._merge_elements(
                fused[duplicate_index],
                element,
            )

        return fused

    def _find_duplicate(
        self,
        candidate: UIElement,
        existing: list[UIElement],
    ) -> int | None:
        """
        Find an existing element representing the same screen component.
        """
        for index, element in enumerate(existing):
            if not self._elements_overlap(candidate, element):
                continue

            if self._text_matches(candidate, element):
                return index

            # If bounding regions overlap significantly and sources differ, fuse them
            if candidate.source != element.source:
                return index

        return None

    def _merge_elements(
        self,
        first: UIElement,
        second: UIElement,
    ) -> UIElement:
        """
        Merge two representations of the same UI element.
        """
        primary = first if first.confidence >= second.confidence else second
        secondary = second if first.confidence >= second.confidence else first

        text = primary.text or secondary.text
        description = primary.description or secondary.description
        element_type = self._select_element_type(primary, secondary)

        confidence = max(primary.confidence, secondary.confidence)
        # Boost confidence when multiple perception sources agree
        if primary.source != secondary.source and primary.has_text() and secondary.has_text():
            confidence = min(1.0, confidence + 0.05)

        attributes = dict(secondary.attributes)
        attributes.update(primary.attributes)

        fused_sources = attributes.get("fused_sources", [])
        if not isinstance(fused_sources, list):
            fused_sources = []
        fused_sources.extend([first.source, second.source])
        attributes["fused_sources"] = list(dict.fromkeys(fused_sources))

        # Combined bounding box
        min_x = min(first.x, second.x)
        min_y = min(first.y, second.y)
        max_x = max(first.x + first.width, second.x + second.width)
        max_y = max(first.y + first.height, second.y + second.height)

        is_enabled = primary.is_enabled and secondary.is_enabled
        is_interactable = primary.is_interactable or secondary.is_interactable

        return UIElement(
            element_id=primary.element_id,
            element_type=element_type,
            text=text,
            description=description,
            x=min_x,
            y=min_y,
            width=max_x - min_x,
            height=max_y - min_y,
            confidence=confidence,
            source="FUSED",
            attributes=attributes,
            is_enabled=is_enabled,
            is_interactable=is_interactable,
            app_name=primary.app_name or secondary.app_name,
            window_title=primary.window_title or secondary.window_title,
        )

    def _select_element_type(
        self,
        primary: UIElement,
        secondary: UIElement,
    ) -> str:
        generic_types = {"", "text", "unknown", "element"}

        if primary.element_type.lower() not in generic_types:
            return primary.element_type

        if secondary.element_type.lower() not in generic_types:
            return secondary.element_type

        return primary.element_type

    # =============================================================
    # GEOMETRY & TEXT
    # =============================================================

    def _elements_overlap(
        self,
        first: UIElement,
        second: UIElement,
    ) -> bool:
        first_center = first.center
        second_center = second.center

        distance_x = abs(first_center[0] - second_center[0])
        distance_y = abs(first_center[1] - second_center[1])

        if (
            distance_x <= self.FUSION_DISTANCE_THRESHOLD
            and distance_y <= self.FUSION_DISTANCE_THRESHOLD
        ):
            return True

        return (
            self._intersection_over_union(first, second)
            >= self.IOU_THRESHOLD
        )

    def _intersection_over_union(
        self,
        first: UIElement,
        second: UIElement,
    ) -> float:
        left = max(first.x, second.x)
        top = max(first.y, second.y)
        right = min(first.x + first.width, second.x + second.width)
        bottom = min(first.y + first.height, second.y + second.height)

        if right <= left or bottom <= top:
            return 0.0

        intersection = (right - left) * (bottom - top)
        first_area = first.area
        second_area = second.area
        union = first_area + second_area - intersection

        if union <= 0:
            return 0.0

        return intersection / union

    def _text_matches(
        self,
        first: UIElement,
        second: UIElement,
    ) -> bool:
        first_text = self._normalize(first.text)
        second_text = self._normalize(second.text)

        if not first_text or not second_text:
            return False

        if first_text == second_text:
            return True

        first_words = set(first_text.split())
        second_words = set(second_text.split())

        if not first_words or not second_words:
            return False

        overlap = len(first_words & second_words) / len(first_words | second_words)
        return overlap >= self.TEXT_SIMILARITY_THRESHOLD

    @staticmethod
    def _normalize(text: str | None) -> str:
        if not text:
            return ""
        return " ".join(text.strip().lower().split())

    @staticmethod
    def _normalize_confidence(confidence: float) -> float:
        try:
            value = float(confidence)
            if value > 1.0:
                value = value / 100.0
        except (TypeError, ValueError):
            return 0.0

        return max(0.0, min(1.0, value))