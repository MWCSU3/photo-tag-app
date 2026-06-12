"""Object detection using YOLOv8 nano model."""

import json
import logging

from app.services.analysis.base import BaseAnalyzer, TagResult

logger = logging.getLogger(__name__)


class ObjectAnalyzer(BaseAnalyzer):
    """Detects objects in images using YOLOv8n (nano model).

    Produces WHAT category tags for detected objects.
    """

    def __init__(self) -> None:
        self._model = None

    async def warmup(self) -> None:
        """Pre-load the YOLOv8n model."""
        try:
            from ultralytics import YOLO

            self._model = YOLO("yolov8n.pt")
            logger.info("ObjectAnalyzer warmed up with YOLOv8n")
        except Exception as e:
            logger.warning(f"ObjectAnalyzer warmup failed: {e}")

    async def analyze(self, image_path: str) -> list[TagResult]:
        """Detect objects in an image using YOLOv8.

        Args:
            image_path: Path to the image file.

        Returns:
            List of TagResult for detected objects.
        """
        tags: list[TagResult] = []

        try:
            from ultralytics import YOLO

            if self._model is None:
                self._model = YOLO("yolov8n.pt")

            results = self._model(image_path, verbose=False)

            seen_objects: dict[str, float] = {}

            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue

                for box in boxes:
                    cls_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    class_name = result.names[cls_id]

                    # Keep the highest confidence detection for each class
                    if class_name not in seen_objects or confidence > seen_objects[class_name]:
                        seen_objects[class_name] = confidence

                    # Get bounding box coordinates
                    xyxy = box.xyxy[0].tolist()
                    bbox = json.dumps({
                        "x": int(xyxy[0]),
                        "y": int(xyxy[1]),
                        "w": int(xyxy[2] - xyxy[0]),
                        "h": int(xyxy[3] - xyxy[1]),
                    })

                    tags.append(TagResult(
                        category="WHAT",
                        value=class_name,
                        confidence=confidence,
                        bounding_box=bbox,
                    ))

        except Exception as e:
            logger.error(f"ObjectAnalyzer error: {e}")

        return tags
