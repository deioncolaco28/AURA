from app.perception.ocr import TesseractOCR
from app.perception.ui_element import UIElement
from app.perception.vlm import VLM
from app.perception.perception_result import (
    PerceptionResult,
)


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

    def __init__(
        self,
        ocr: TesseractOCR | None = None,
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
        Analyze an image using the configured perception sources.
        """

        elements: list[UIElement] = []
        sources_used: list[str] = []
        screen_description = ""

        if self.ocr is not None:
            ocr_elements = self._run_ocr(image)

            if ocr_elements:
                elements.extend(ocr_elements)

            sources_used.append("OCR")

        if self.vlm is not None:
            vlm_result = self.vlm.analyze(
                image,
                instruction=instruction,
            )

            vlm_elements = self._convert_vlm_elements(
                vlm_result.elements
            )

            if vlm_elements:
                elements.extend(vlm_elements)

            sources_used.append("VLM")

            screen_description = (
                vlm_result.description
            )

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
            },
        )

    def _run_ocr(
        self,
        image,
    ) -> list[UIElement]:
        """
        Run OCR and convert OCR elements into UIElements.
        """

        results = self.ocr.detect_text(
            image
        )

        elements = []

        for index, element in enumerate(
            results
        ):
            elements.append(
                UIElement(
                    element_id=f"ocr-{index}",
                    element_type="text",
                    text=element.text,
                    x=element.x,
                    y=element.y,
                    width=element.width,
                    height=element.height,
                    confidence=element.confidence,
                    source="OCR",
                )
            )

        return elements

    def _convert_vlm_elements(
        self,
        vlm_elements,
    ) -> list[UIElement]:
        """
        Convert VLMElement objects into UIElement objects.
        """

        elements = []

        for index, element in enumerate(
            vlm_elements
        ):
            elements.append(
                UIElement(
                    element_id=f"vlm-{index}",
                    element_type=element.element_type,
                    text=element.text,
                    description=element.description,
                    x=element.x,
                    y=element.y,
                    width=element.width,
                    height=element.height,
                    confidence=element.confidence,
                    source="VLM",
                    attributes=dict(
                        element.attributes
                    ),
                )
            )

        return elements

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

            duplicate_index = (
                self._find_duplicate(
                    element,
                    fused,
                )
            )

            if duplicate_index is None:
                fused.append(element)
                continue

            fused[
                duplicate_index
            ] = self._merge_elements(
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
        Find an existing element that represents
        the same screen component.
        """

        for index, element in enumerate(
            existing
        ):

            if self._elements_overlap(
                candidate,
                element,
            ):
                if self._text_matches(
                    candidate,
                    element,
                ):
                    return index

                if (
                    candidate.source
                    != element.source
                ):
                    return index

        return None

    def _merge_elements(
        self,
        first: UIElement,
        second: UIElement,
    ) -> UIElement:
        """
        Merge two representations of the same element.

        VLM information is preferred for semantic description,
        while OCR text is preserved when available.
        """

        primary = first
        secondary = second

        if (
            secondary.confidence
            > primary.confidence
        ):
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

        element_type = (
            primary.element_type
            if primary.element_type != "text"
            else secondary.element_type
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

        attributes[
            "fused_sources"
        ] = list(
            dict.fromkeys(
                [
                    first.source,
                    second.source,
                ]
            )
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
            width=max(
                first.x + first.width,
                second.x + second.width,
            )
            - min(
                first.x,
                second.x,
            ),
            height=max(
                first.y + first.height,
                second.y + second.height,
            )
            - min(
                first.y,
                second.y,
            ),
            confidence=confidence,
            source="FUSED",
            attributes=attributes,
        )

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

        return self._intersection_over_union(
            first,
            second,
        ) >= 0.30

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

        if (
            first_text == second_text
        ):
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

    def _intersection_over_union(
        self,
        first: UIElement,
        second: UIElement,
    ) -> float:
        """Calculate bounding-box IoU."""

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

    @staticmethod
    def _normalize(
        text: str | None,
    ) -> str:
        if not text:
            return ""

        return " ".join(
            text.strip().lower().split()
        )