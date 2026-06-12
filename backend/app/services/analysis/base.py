"""Base class for all ML analyzers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class TagResult:
    """Result from an analyzer representing a detected tag."""

    category: str  # WHO, FACES, WHAT, WHERE
    value: str
    confidence: float
    bounding_box: str | None = None
    embedding: bytes | None = field(default=None, repr=False)


class BaseAnalyzer(ABC):
    """Abstract base class for ML analyzers."""

    @abstractmethod
    async def analyze(self, image_path: str) -> list[TagResult]:
        """Analyze an image and return detected tags.

        Args:
            image_path: Path to the image file on disk.

        Returns:
            List of TagResult objects with detected features.
        """
        pass

    @abstractmethod
    async def warmup(self) -> None:
        """Pre-load models to avoid cold start on first request."""
        pass
