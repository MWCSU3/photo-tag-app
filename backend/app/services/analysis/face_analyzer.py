"""Face detection and analysis using DeepFace."""

import json
import logging
from typing import Any

from app.services.analysis.base import BaseAnalyzer, TagResult

logger = logging.getLogger(__name__)


class FaceAnalyzer(BaseAnalyzer):
    """Analyzes faces in images using DeepFace.

    Detects faces and extracts attributes like age, gender, emotion.
    Produces WHO category tags (person attributes) and FACES category tags.
    """

    def __init__(self) -> None:
        self._initialized = False

    async def warmup(self) -> None:
        """Pre-load DeepFace models."""
        try:
            from deepface import DeepFace  # noqa: F401

            self._initialized = True
            logger.info("FaceAnalyzer warmed up successfully")
        except Exception as e:
            logger.warning(f"FaceAnalyzer warmup failed: {e}")

    async def analyze(self, image_path: str) -> list[TagResult]:
        """Detect faces and extract attributes from an image.

        Args:
            image_path: Path to the image file.

        Returns:
            List of TagResult for detected faces with attributes.
        """
        tags: list[TagResult] = []

        try:
            from deepface import DeepFace

            # Analyze faces in the image
            results: list[dict[str, Any]] = DeepFace.analyze(
                img_path=image_path,
                actions=["age", "gender", "emotion"],
                enforce_detection=False,
                silent=True,
            )

            if not isinstance(results, list):
                results = [results]

            for i, face in enumerate(results):
                # Skip if no face region found (DeepFace returns full image region)
                region = face.get("region", {})
                if not region or (region.get("w", 0) == 0 and region.get("h", 0) == 0):
                    continue

                bbox = json.dumps({
                    "x": region.get("x", 0),
                    "y": region.get("y", 0),
                    "w": region.get("w", 0),
                    "h": region.get("h", 0),
                })

                # Add FACES tag for face detection
                face_confidence = face.get("face_confidence", 0.8)
                if isinstance(face_confidence, (int, float)) and face_confidence > 0.3:
                    tags.append(TagResult(
                        category="FACES",
                        value=f"face_{i + 1}",
                        confidence=float(face_confidence),
                        bounding_box=bbox,
                    ))

                    # Age attribute -> WHO tag
                    age = face.get("age")
                    if age is not None:
                        tags.append(TagResult(
                            category="WHO",
                            value=f"age_{age}",
                            confidence=float(face_confidence),
                            bounding_box=bbox,
                        ))

                    # Gender attribute -> WHO tag
                    dominant_gender = face.get("dominant_gender")
                    if dominant_gender:
                        gender_conf = face.get("gender", {})
                        conf_value = gender_conf.get(dominant_gender, 0.8) if isinstance(gender_conf, dict) else 0.8
                        tags.append(TagResult(
                            category="WHO",
                            value=dominant_gender.lower(),
                            confidence=float(conf_value) / 100.0 if conf_value > 1 else float(conf_value),
                            bounding_box=bbox,
                        ))

                    # Emotion attribute -> WHO tag
                    dominant_emotion = face.get("dominant_emotion")
                    if dominant_emotion:
                        emotion_conf = face.get("emotion", {})
                        conf_value = emotion_conf.get(dominant_emotion, 0.8) if isinstance(emotion_conf, dict) else 0.8
                        tags.append(TagResult(
                            category="WHO",
                            value=f"emotion_{dominant_emotion}",
                            confidence=float(conf_value) / 100.0 if conf_value > 1 else float(conf_value),
                            bounding_box=bbox,
                        ))

        except Exception as e:
            logger.error(f"FaceAnalyzer error: {e}")

        return tags
