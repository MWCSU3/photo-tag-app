"""Shared API dependencies."""

from app.database import get_db
from app.services.analysis.pipeline import AnalysisPipeline

# Singleton pipeline instance
_pipeline: AnalysisPipeline | None = None


async def get_analysis_pipeline() -> AnalysisPipeline:
    """Get or create the analysis pipeline singleton."""
    global _pipeline
    if _pipeline is None:
        _pipeline = AnalysisPipeline()
    return _pipeline


__all__ = ["get_db", "get_analysis_pipeline"]
