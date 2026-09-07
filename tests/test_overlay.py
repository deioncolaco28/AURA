from app.tutoring.overlay import HighlightOverlay


def test_overlay_can_be_created():
    overlay = HighlightOverlay()

    assert overlay.root is None