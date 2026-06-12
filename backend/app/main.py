"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes.photos import router as photos_router
from app.api.routes.tags import router as tags_router
from app.config import settings
from app.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.

    On startup: initializes the database and warms up ML models.
    """
    logger.info("Starting up Photo Tagger backend...")

    # Ensure upload directory exists
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Ensure model cache directory exists
    settings.MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Warm up ML pipeline
    try:
        from app.api.dependencies import get_analysis_pipeline

        pipeline = await get_analysis_pipeline()
        await pipeline.warmup()
        logger.info("ML pipeline warmed up")
    except Exception as e:
        logger.warning(f"ML pipeline warmup failed (will retry on first request): {e}")

    yield

    logger.info("Shutting down Photo Tagger backend...")


app = FastAPI(
    title="Photo Tagger API",
    description="ML-powered photo analysis and tagging service",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(photos_router)
app.include_router(tags_router)

# Serve uploaded photos as static files
# Ensure the uploads directory exists before mounting
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")

# Serve static files (test page, etc.)
STATIC_DIR = Path(__file__).parent.parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/test")
async def test_page():
    """Serve the test HTML page for photo tagging."""
    return FileResponse(str(STATIC_DIR / "test.html"), media_type="text/html")
