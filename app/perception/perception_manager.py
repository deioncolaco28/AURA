from app.perception.ocr import OCR
from app.perception.perception_result import (
    PerceptionResult,
)
from app.perception.ui_element import UIElement
from app.perception.vlm import VLM


class PerceptionManager:
    """Coordinates different perception systems."""

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
        """Analyze a screenshot using available systems."""

        elements = []
        sources_used = []
        screen_description = ""

        if self.ocr is not None:
            ocr_elements = self._analyze_ocr(
                image
            )

            elements.extend(
                ocr_elements
            )

            sources_used.append("OCR")

        if self.vlm is not None:
            vlm_result = self.vlm.analyze(
                image,
                instruction,
            )

            vlm_elements = self._convert_vlm_elements(
                vlm_result.elements
            )

            elements.extend(
                vlm_elements
            )

            screen_description = (
                vlm_result.description
            )

            sources_used.append("VLM")

        return PerceptionResult(
            elements=elements,
            screen_description=(
                screen_description
            ),
            sources_used=sources_used,
        )

    def _analyze_ocr(
        self,
        image,
    ) -> list[UIElement]:
        """Convert OCR results into unified elements."""

        if self.ocr is None:
            return []

        text_elements = (
            self.ocr.detect_text(image)
        )

        elements = []

        for index, element in enumerate(
            text_elements
        ):
            elements.append(
                UIElement(
                    element_id=f"ocr_{index}",
                    element_type="TEXT",
                    text=element.text,
                    x=element.x,
                    y=element.y,
                    width=element.width,
                    height=element.height,
                    confidence=(
                        element.confidence / 100.0
                    ),
                    source="OCR",
                )
            )

        return elements

    def _convert_vlm_elements(
        self,
        vlm_elements,
    ) -> list[UIElement]:
        """Convert VLM elements into unified elements."""

        elements = []

        for index, element in enumerate(
            vlm_elements
        ):
            elements.append(
                UIElement(
                    element_id=f"vlm_{index}",
                    element_type=(
                        element.element_type
                    ),
                    text=element.text,
                    x=element.x,
                    y=element.y,
                    width=element.width,
                    height=element.height,
                    confidence=(
                        element.confidence
                    ),
                    source="VLM",
                    attributes=(
                        element.attributes
                    ),
                )
            )

        return elements