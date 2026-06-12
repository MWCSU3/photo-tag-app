"""Photo API endpoints."""

import json
import math
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_analysis_pipeline, get_db
from app.config import settings
from app.schemas.photo import PhotoListResponse, PhotoResponse, TagResponse
from app.services import photo_service
from app.services.analysis.pipeline import AnalysisPipeline

router = APIRouter(prefix="/api/photos", tags=["photos"])


@router.post("/upload", response_model=PhotoResponse)
async def upload_photo(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    pipeline: AnalysisPipeline = Depends(get_analysis_pipeline),
) -> PhotoResponse:
    """Upload a photo and run ML analysis on it.

    Accepts an image file, saves it to the uploads directory, then runs
    the full analysis pipeline (face detection, object detection, scene
    classification) and returns the photo with all detected tags.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Validate extension
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type {ext} not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}",
        )

    # Read file content
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {settings.MAX_FILE_SIZE} bytes",
        )

    # Save upload
    photo = await photo_service.save_upload(content, file.filename, db)

    # Run analysis
    photo = await photo_service.analyze_photo(photo, pipeline, db)

    return PhotoResponse.model_validate(photo)


@router.get("", response_model=PhotoListResponse)
async def list_photos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("upload_date"),
    sort_order: str = Query("desc"),
    categories: str | None = Query(None),
    group_by: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> PhotoListResponse:
    """List photos with pagination, sorting, and filtering.

    The categories parameter accepts a JSON string of {category: [values]}.
    """
    parsed_categories = None
    if categories:
        try:
            parsed_categories = json.loads(categories)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid categories JSON")

    photos, total = await photo_service.get_photos(
        db=db,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        categories=parsed_categories,
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return PhotoListResponse(
        photos=[PhotoResponse.model_validate(p) for p in photos],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{photo_id}", response_model=PhotoResponse)
async def get_photo(
    photo_id: int,
    db: AsyncSession = Depends(get_db),
) -> PhotoResponse:
    """Get a single photo by ID with all its tags."""
    photo = await photo_service.get_photo_by_id(photo_id, db)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    return PhotoResponse.model_validate(photo)


@router.delete("/{photo_id}")
async def delete_photo(
    photo_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a photo and its associated file and tags."""
    deleted = await photo_service.delete_photo(photo_id, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Photo not found")
    return {"detail": "Photo deleted successfully"}
