"""Scene classification based on detected objects.

Uses object combinations to infer scene/location context.
"""

import logging

from app.services.analysis.base import BaseAnalyzer, TagResult

logger = logging.getLogger(__name__)

# Mapping of object combinations to scene labels
SCENE_RULES: list[tuple[set[str], str, float]] = [
    # (required_objects, scene_label, base_confidence)
    ({"car", "truck", "traffic light"}, "street", 0.8),
    ({"car", "bus"}, "street", 0.75),
    ({"car"}, "outdoors", 0.5),
    ({"airplane"}, "airport", 0.7),
    ({"boat"}, "waterfront", 0.7),
    ({"train"}, "train_station", 0.7),
    ({"bed", "clock"}, "bedroom", 0.8),
    ({"bed"}, "bedroom", 0.7),
    ({"couch", "tv"}, "living_room", 0.8),
    ({"couch"}, "living_room", 0.65),
    ({"dining table", "chair"}, "dining_room", 0.8),
    ({"oven", "refrigerator"}, "kitchen", 0.85),
    ({"oven"}, "kitchen", 0.7),
    ({"refrigerator"}, "kitchen", 0.7),
    ({"microwave"}, "kitchen", 0.65),
    ({"sink", "toilet"}, "bathroom", 0.85),
    ({"toilet"}, "bathroom", 0.8),
    ({"laptop", "keyboard", "mouse"}, "office", 0.8),
    ({"laptop", "keyboard"}, "office", 0.7),
    ({"laptop"}, "workspace", 0.5),
    ({"book"}, "library", 0.4),
    ({"sports ball", "person"}, "sports_field", 0.7),
    ({"tennis racket"}, "tennis_court", 0.75),
    ({"surfboard"}, "beach", 0.75),
    ({"ski", "snowboard"}, "ski_resort", 0.8),
    ({"potted plant", "vase"}, "garden", 0.6),
    ({"dog", "cat"}, "home", 0.5),
    ({"horse", "cow", "sheep"}, "farm", 0.8),
    ({"cow", "sheep"}, "farm", 0.75),
    ({"horse"}, "outdoors", 0.5),
    ({"bench"}, "park", 0.6),
    ({"umbrella", "person"}, "outdoors", 0.5),
    ({"backpack", "person"}, "outdoors", 0.4),
    ({"fork", "knife", "cup"}, "dining", 0.7),
    ({"wine glass", "bottle"}, "restaurant", 0.7),
    ({"cake"}, "celebration", 0.5),
]


class SceneAnalyzer(BaseAnalyzer):
    """Classifies scene/location based on detected objects.

    Uses rule-based inference from YOLO detection results to produce
    WHERE category tags representing the likely location/scene.
    """

    def __init__(self) -> None:
        self._detected_objects: set[str] = set()

    async def warmup(self) -> None:
        """No model to load for rule-based classification."""
        logger.info("SceneAnalyzer ready (rule-based)")

    async def analyze(self, image_path: str) -> list[TagResult]:
        """Classify scene based on objects detected by YOLO.

        This analyzer runs YOLOv8 to get objects, then applies rules
        to infer the scene/location.

        Args:
            image_path: Path to the image file.

        Returns:
            List of TagResult for inferred scenes/locations.
        """
        tags: list[TagResult] = []

        try:
            from ultralytics import YOLO

            model = YOLO("yolov8n.pt")
            results = model(image_path, verbose=False)

            detected_objects: set[str] = set()
            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue
                for box in boxes:
                    cls_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    if confidence >= 0.3:
                        class_name = result.names[cls_id]
                        detected_objects.add(class_name)

            if not detected_objects:
                return tags

            # Apply scene rules
            matched_scenes: dict[str, float] = {}
            for required_objects, scene_label, base_confidence in SCENE_RULES:
                if required_objects.issubset(detected_objects):
                    # Scale confidence by how many required objects matched
                    match_ratio = len(required_objects) / max(len(detected_objects), 1)
                    confidence = min(base_confidence + match_ratio * 0.1, 0.99)
                    if scene_label not in matched_scenes or confidence > matched_scenes[scene_label]:
                        matched_scenes[scene_label] = confidence

            for scene_label, confidence in matched_scenes.items():
                tags.append(TagResult(
                    category="WHERE",
                    value=scene_label,
                    confidence=confidence,
                ))

            # If we have objects but no scene matched, label as "general"
            if not tags and detected_objects:
                tags.append(TagResult(
                    category="WHERE",
                    value="indoor" if any(
                        obj in detected_objects
                        for obj in ["couch", "bed", "chair", "tv", "laptop", "book"]
                    ) else "outdoor",
                    confidence=0.4,
                ))

        except Exception as e:
            logger.error(f"SceneAnalyzer error: {e}")

        return tags
