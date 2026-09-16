from app.perception.ocr import OCR, TesseractOCR
from app.perception.ui_element import UIElement
from app.perception.vlm import VLM
from app.perception.perception_result import PerceptionResult


class PerceptionManager:
    """
    Coordinates OCR and VLM perception.

    Pipeline:

        Screenshot
            ↓
        OCR + VLM
            ↓
        Convert to UIElement
            ↓
        Fuse overlapping / duplicate elements
            ↓
        PerceptionResult
    """

    FUSION_DISTANCE_THRESHOLD = 40
    TEXT_SIMILARITY_THRESHOLD = 0.70
    IOU_THRESHOLD = 0.30

    def __init__(
        self,
        ocr: OCR | None = None,
        vlm: VLM | None = None,
    ):
        self.ocr = ocr
        self.vlm = vlm

    def analyze(
        self,
        image,
        instruction: str | None = None,
    ) -> PerceptionResult:
        """
        Analyze a screenshot using the configured perception sources.

        OCR provides text and coordinates.
        VLM provides semantic understanding and visual descriptions.
        Both sources are fused into a unified UI representation.
        """

        elements: list[UIElement] = []
        sources_used: list[str] = []
        screen_description = ""

        # ---------------------------------------------------------
        # OCR perception
        # ---------------------------------------------------------

        if self.ocr is not None:
            ocr_elements = self._run_ocr(image)

            elements.extend(ocr_elements)

            sources_used.append("OCR")

        # ---------------------------------------------------------
        # VLM perception
        # ---------------------------------------------------------

        if self.vlm is not None:
            vlm_result = self.vlm.analyze(
                image,
                instruction=instruction,
            )

            vlm_elements = self._convert_vlm_elements(
                vlm_result.elements
            )

            elements.extend(vlm_elements)

            sources_used.append("VLM")

            screen_description = (
                vlm_result.description
            )

        # ---------------------------------------------------------
        # Fusion
        # ---------------------------------------------------------

        fused_elements = self._fuse_elements(
            elements
        )

        return PerceptionResult(
            elements=fused_elements,
            screen_description=screen_description,
            sources_used=sources_used,
            screenshot=image,
            metadata={
                "raw_element_count": len(elements),
                "fused_element_count": len(
                    fused_elements
                ),
                "fusion_applied": (
                    len(elements)
                    != len(fused_elements)
                ),
                "instruction": instruction,
                "ocr_enabled": self.ocr is not None,
                "vlm_enabled": self.vlm is not None,
            },
        )

    # =============================================================
    # OCR
    # =============================================================

    def _run_ocr(
        self,
        image,
    ) -> list[UIElement]:
        """
        Run OCR and convert OCR results into UIElements.
        """

        results = self.ocr.detect_text(image)

        elements: list[UIElement] = []

        for index, element in enumerate(results):
            elements.append(
                UIElement(
                    element_id=f"ocr-{index}",
                    element_type="text",
                    text=element.text,
                    x=element.x,
                    y=element.y,
                    width=element.width,
                    height=element.height,
                    confidence=(
                        self._normalize_confidence(
                            element.confidence
                        )
                    ),
                    source="OCR",
                )
            )

        return elements

    # =============================================================
    # VLM
    # =============================================================

    def _convert_vlm_elements(
        self,
        vlm_elements,
    ) -> list[UIElement]:
        """
        Convert VLMElement objects into UIElements.
        """

        elements: list[UIElement] = []

        for index, element in enumerate(vlm_elements):
            element_id = (
                element.element_id
                or f"vlm-{index}"
            )

            elements.append(
                UIElement(
                    element_id=element_id,
                    element_type=element.element_type,
                    text=element.text,
                    description=element.description,
                    x=element.x,
                    y=element.y,
                    width=element.width,
                    height=element.height,
                    confidence=(
                        self._normalize_confidence(
                            element.confidence
                        )
                    ),
                    source="VLM",
                    attributes=dict(
                        element.attributes
                    ),
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
        Merge OCR/VLM elements referring to the same
        visual UI component.
        """

        fused: list[UIElement] = []

        for element in elements:
            duplicate_index = self._find_duplicate(
                element,
                fused,
            )

            if duplicate_index is None:
                fused.append(element)
                continue

            fused[duplicate_index] = (
                self._merge_elements(
                    fused[duplicate_index],
                    element,
                )
            )

        return fused

    def _find_duplicate(
        self,
        candidate: UIElement,
        existing: list[UIElement],
    ) -> int | None:
        """
        Find an existing element representing the
        same screen component.
        """

        for index, element in enumerate(existing):

            if not self._elements_overlap(
                candidate,
                element,
            ):
                continue

            if self._text_matches(
                candidate,
                element,
            ):
                return index

            # OCR and VLM may describe the same element
            # differently. If their bounding regions overlap
            # and they originate from different sources,
            # treat them as the same UI component.
            if candidate.source != element.source:
                return index

        return None

    def _merge_elements(
        self,
        first: UIElement,
        second: UIElement,
    ) -> UIElement:
        """
        Merge two representations of the same element.

        OCR text is preserved.
        VLM semantic descriptions are preserved.
        Higher-confidence information becomes primary.
        """

        primary = first
        secondary = second

        if secondary.confidence > primary.confidence:
            primary, secondary = (
                secondary,
                primary,
            )

        text = (
            primary.text
            or secondary.text
        )

        description = (
            primary.description
            or secondary.description
        )

        element_type = self._select_element_type(
            primary,
            secondary,
        )

        confidence = max(
            primary.confidence,
            secondary.confidence,
        )

        attributes = dict(
            secondary.attributes
        )

        attributes.update(
            primary.attributes
        )

        fused_sources = attributes.get(
            "fused_sources",
            [],
        )

        if not isinstance(fused_sources, list):
            fused_sources = []

        fused_sources.extend(
            [
                first.source,
                second.source,
            ]
        )

        attributes["fused_sources"] = list(
            dict.fromkeys(fused_sources)
        )

        return UIElement(
            element_id=primary.element_id,
            element_type=element_type,
            text=text,
            description=description,
            x=min(
                first.x,
                second.x,
            ),
            y=min(
                first.y,
                second.y,
            ),
            width=(
                max(
                    first.x + first.width,
                    second.x + second.width,
                )
                - min(
                    first.x,
                    second.x,
                )
            ),
            height=(
                max(
                    first.y + first.height,
                    second.y + second.height,
                )
                - min(
                    first.y,
                    second.y,
                )
            ),
            confidence=confidence,
            source="FUSED",
            attributes=attributes,
        )

    def _select_element_type(
        self,
        primary: UIElement,
        secondary: UIElement,
    ) -> str:
        """
        Prefer a semantic VLM element type over a generic OCR type.
        """

        generic_types = {
            "",
            "text",
            "unknown",
        }

        if primary.element_type.lower() not in generic_types:
            return primary.element_type

        if secondary.element_type.lower() not in generic_types:
            return secondary.element_type

        return primary.element_type

    # =============================================================
    # GEOMETRY
    # =============================================================

    def _elements_overlap(
        self,
        first: UIElement,
        second: UIElement,
    ) -> bool:
        """
        Determine whether two UI elements occupy
        approximately the same screen region.
        """

        first_center = first.center
        second_center = second.center

        distance_x = abs(
            first_center[0]
            - second_center[0]
        )

        distance_y = abs(
            first_center[1]
            - second_center[1]
        )

        if (
            distance_x
            <= self.FUSION_DISTANCE_THRESHOLD
            and distance_y
            <= self.FUSION_DISTANCE_THRESHOLD
        ):
            return True

        return (
            self._intersection_over_union(
                first,
                second,
            )
            >= self.IOU_THRESHOLD
        )

    def _intersection_over_union(
        self,
        first: UIElement,
        second: UIElement,
    ) -> float:
        """
        Calculate bounding-box IoU.
        """

        left = max(
            first.x,
            second.x,
        )

        top = max(
            first.y,
            second.y,
        )

        right = min(
            first.x + first.width,
            second.x + second.width,
        )

        bottom = min(
            first.y + first.height,
            second.y + second.height,
        )

        if (
            right <= left
            or bottom <= top
        ):
            return 0.0

        intersection = (
            (right - left)
            * (bottom - top)
        )

        first_area = (
            first.width
            * first.height
        )

        second_area = (
            second.width
            * second.height
        )

        union = (
            first_area
            + second_area
            - intersection
        )

        if union <= 0:
            return 0.0

        return intersection / union

    # =============================================================
    # TEXT MATCHING
    # =============================================================

    def _text_matches(
        self,
        first: UIElement,
        second: UIElement,
    ) -> bool:
        """
        Determine whether two elements have sufficiently
        similar textual information.
        """

        first_text = self._normalize(
            first.text
        )

        second_text = self._normalize(
            second.text
        )

        if not first_text or not second_text:
            return False

        if first_text == second_text:
            return True

        first_words = set(
            first_text.split()
        )

        second_words = set(
            second_text.split()
        )

        if not first_words or not second_words:
            return False

        overlap = (
            len(
                first_words
                & second_words
            )
            / len(
                first_words
                | second_words
            )
        )

        return (
            overlap
            >= self.TEXT_SIMILARITY_THRESHOLD
        )

    # =============================================================
    # HELPERS
    # =============================================================

    @staticmethod
    def _normalize(
        text: str | None,
    ) -> str:
        if not text:
            return ""

        return " ".join(
            text.strip().lower().split()
        )

    @staticmethod
    def _normalize_confidence(
        confidence: float,
    ) -> float:
        """
        Keep confidence values in the standard
        0.0–1.0 range.
        """

        try:
            value = float(confidence)
        except (TypeError, ValueError):
            return 0.0

        return max(
            0.0,
            min(1.0, value),
        )