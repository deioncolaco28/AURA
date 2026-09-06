from app.perception.ocr import TextElement


class UIGrounder:
    """Locates UI elements based on detected screen content."""

    def find_text(
        self,
        elements: list[TextElement],
        target: str,
    ) -> TextElement | None:
        """Find a text element matching the requested target."""

        target_normalized = target.strip().lower()

        if not target_normalized:
            return None

        for element in elements:
            if element.text.strip().lower() == target_normalized:
                return element

        return None