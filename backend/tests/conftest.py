"""Pytest fixtures and configuration for tests."""

import asyncio
import io
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app
from app.services.analysis.base import TagResult
from app.services.analysis.pipeline import AnalysisPipeline


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_db():
    """Create a test database with clean tables."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def mock_pipeline():
    """Create a mock analysis pipeline that returns predictable results."""
    pipeline = AnalysisPipeline()

    # Mock the analyze method to return test tags without running ML models
    mock_results = [
        TagResult(category="WHAT", value="person", confidence=0.95),
        TagResult(category="WHAT", value="dog", confidence=0.87),
        TagResult(category="WHERE", value="park", confidence=0.72),
        TagResult(category="FACES", value="face_1", confidence=0.91),
        TagResult(category="WHO", value="age_25", confidence=0.8),
    ]
    pipeline.analyze = AsyncMock(return_value=mock_results)
    return pipeline


@pytest_asyncio.fixture
async def client(test_db, mock_pipeline, tmp_path):
    """Create a test HTTP client with mocked dependencies."""
    from app.config import settings

    # Override upload directory to temp path
    original_upload_dir = settings.UPLOAD_DIR
    settings.UPLOAD_DIR = tmp_path / "uploads"
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    async def override_get_db():
        yield test_db

    async def override_get_pipeline():
        return mock_pipeline

    app.dependency_overrides[get_db] = override_get_db

    from app.api.dependencies import get_analysis_pipeline
    app.dependency_overrides[get_analysis_pipeline] = override_get_pipeline

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    settings.UPLOAD_DIR = original_upload_dir


@pytest.fixture
def sample_image(tmp_path) -> bytes:
    """Create a simple test image."""
    img = Image.new("RGB", (100, 100), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.fixture
def sample_image_file(sample_image) -> tuple[str, bytes, str]:
    """Return a tuple suitable for httpx file upload."""
    return ("file", ("test_photo.jpg", sample_image, "image/jpeg"))
