"""Analysis pipeline that orchestrates all ML analyzers."""

import logging

from app.services.analysis.base import BaseAnalyzer, TagResult
from app.services.analysis.face_analyzer import FaceAnalyzer
from app.services.analysis.object_analyzer import ObjectAnalyzer
from app.services.analysis.scene_analyzer import SceneAnalyzer

logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """Orchestrates multiple ML analyzers and combines their results.

    Runs face detection, object detection, and scene classification
    on an image, then deduplicates and returns the combined tag results.
    """

    def __init__(self) -> None:
        self.analyzers: list[BaseAnalyzer] = [
            FaceAnalyzer(),
            ObjectAnalyzer(),
            SceneAnalyzer(),
        ]

    async def warmup(self) -> None:
        """Warm up all analyzers by pre-loading their models."""
        for analyzer in self.analyzers:
            try:
                await analyzer.warmup()
            except Exception as e:
                logger.warning(f"Failed to warm up {analyzer.__class__.__name__}: {e}")

    async def analyze(self, image_path: str) -> list[TagResult]:
        """Run all analyzers on an image and return combined results.

        Args:
            image_path: Path to the image file to analyze.

        Returns:
            Deduplicated list of TagResult from all analyzers.
        """
        all_tags: list[TagResult] = []

        for analyzer in self.analyzers:
            try:
                tags = await analyzer.analyze(image_path)
                all_tags.extend(tags)
            except Exception as e:
                logger.error(
                    f"Analyzer {analyzer.__class__.__name__} failed: {e}"
                )

        return self._deduplicate(all_tags)

    def _deduplicate(self, tags: list[TagResult]) -> list[TagResult]:
        """Remove duplicate tags, keeping the highest confidence version.

        Tags are considered duplicates if they share the same category and value.
        """
        best_tags: dict[tuple[str, str], TagResult] = {}

        for tag in tags:
            key = (tag.category, tag.value)
            if key not in best_tags or tag.confidence > best_tags[key].confidence:
                best_tags[key] = tag

        return list(best_tags.values())
