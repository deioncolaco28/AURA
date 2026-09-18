"""
app/perception/config.py

Centralized configuration for computer perception, UI understanding,
grounding, target ranking, and observation diffing in AURA.
"""

from dataclasses import dataclass, field


@dataclass
class PerceptionConfig:
    """Centralized thresholds and configuration parameters for perception."""

    # Confidence thresholds
    minimum_ocr_confidence: float = 0.50
    minimum_vlm_confidence: float = 0.60
    minimum_accessibility_confidence: float = 0.85
    minimum_grounding_confidence: float = 0.60
    minimum_target_confidence: float = 0.65

    # Target ranking & ambiguity
    ambiguity_margin: float = 0.12
    minimum_score_threshold: float = 0.35

    # Multi-source fusion thresholds
    fusion_distance_threshold: int = 40
    fusion_iou_threshold: float = 0.30
    text_similarity_threshold: float = 0.70

    # Observation and polling
    observation_timeout: float = 15.0
    polling_interval: float = 0.25

    # Spatial reasoning tolerances
    row_tolerance_px: int = 20
    column_tolerance_px: int = 20
    proximity_max_distance_px: int = 400

    # Caching
    cache_enabled: bool = True
    cache_ttl_seconds: float = 2.0

    # Scrolling
    max_scroll_attempts: int = 5
    scroll_step_px: int = 400

    # Feature weights for target ranking
    ranking_weights: dict[str, float] = field(
        default_factory=lambda: {
            "text_similarity": 0.35,
            "description_similarity": 0.10,
            "element_type": 0.10,
            "element_confidence": 0.10,
            "spatial_score": 0.15,
            "ordinal_score": 0.10,
            "foreground_match": 0.05,
            "interactability": 0.05,
        }
    )
