"""Photo business logic service."""

import json
import uuid
from datetime import datetime
from pathlib import Path

from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.photo import FaceEmbedding, Photo, Tag, TagCategory
from app.services.analysis.base import TagResult
from app.services.analysis.pipeline import AnalysisPipeline


async def save_upload(
    file_content: bytes,
    original_filename: str,
    db: AsyncSession,
) -> Photo:
    """Save an uploaded file and create a Photo record.

    Args:
        file_content: Raw file bytes.
        original_filename: Original filename from the upload.
        db: Async database session.

    Returns:
        Created Photo model instance.
    """
    # Generate unique filename
    ext = Path(original_filename).suffix.lower()
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    upload_dir = settings.UPLOAD_DIR
    upload_dir.mkdir(parents=True, exist_ok=True)
    filepath = upload_dir / unique_filename

    # Write file to disk
    filepath.write_bytes(file_content)

    # Validate file is a real image and get dimensions
    width, height = None, None
    try:
        with Image.open(filepath) as img:
            img.verify()
        # Re-open after verify() since verify() may leave file in unusable state
        with Image.open(filepath) as img:
            width, height = img.size
    except Exception:
        # Invalid image file - clean up and raise
        filepath.unlink(missing_ok=True)
        raise ValueError("Uploaded file is not a valid image")

    # Create database record
    photo = Photo(
        filename=unique_filename,
        original_filename=original_filename,
        filepath=str(filepath),
        file_size=len(file_content),
        width=width,
        height=height,
        upload_date=datetime.utcnow(),
    )
    db.add(photo)
    await db.commit()
    await db.refresh(photo)

    return photo


async def analyze_photo(
    photo: Photo,
    pipeline: AnalysisPipeline,
    db: AsyncSession,
) -> Photo:
    """Run the ML analysis pipeline on a photo and store results.

    Args:
        photo: Photo model instance to analyze.
        pipeline: Configured analysis pipeline.
        db: Async database session.

    Returns:
        Updated Photo model with tags.
    """
    tag_results: list[TagResult] = await pipeline.analyze(photo.filepath)

    for result in tag_results:
        tag = Tag(
            photo_id=photo.id,
            category=TagCategory(result.category),
            value=result.value,
            confidence=result.confidence,
            bounding_box=result.bounding_box,
        )
        db.add(tag)

        # If this is a face with an embedding, save it
        if result.embedding and result.category == "FACES":
            await db.flush()  # Get the tag id
            face_embedding = FaceEmbedding(
                photo_id=photo.id,
                tag_id=tag.id,
                embedding_vector=result.embedding,
            )
            db.add(face_embedding)

    photo.analyzed = True
    photo.analysis_date = datetime.utcnow()
    await db.commit()

    # Reload with tags
    result = await db.execute(
        select(Photo).options(selectinload(Photo.tags)).where(Photo.id == photo.id)
    )
    return result.scalar_one()


async def get_photos(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "upload_date",
    sort_order: str = "desc",
    categories: dict[str, list[str]] | None = None,
) -> tuple[list[Photo], int]:
    """Get paginated list of photos with optional filtering.

    Args:
        db: Async database session.
        page: Page number (1-indexed).
        page_size: Number of items per page.
        sort_by: Field to sort by.
        sort_order: Sort direction ('asc' or 'desc').
        categories: Filter by tag categories {category: [values]}.

    Returns:
        Tuple of (photos list, total count).
    """
    query = select(Photo).options(selectinload(Photo.tags))

    # Apply category filters
    if categories:
        for category, values in categories.items():
            try:
                cat_enum = TagCategory(category)
                query = query.where(
                    Photo.tags.any(
                        (Tag.category == cat_enum) & (Tag.value.in_(values))
                    )
                )
            except ValueError:
                pass

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply sorting (allowlist valid columns to prevent attribute probing)
    ALLOWED_SORT_FIELDS = {"upload_date", "file_size", "original_filename"}
    sort_column = getattr(Photo, sort_by) if sort_by in ALLOWED_SORT_FIELDS else Photo.upload_date
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    photos = list(result.scalars().unique().all())

    return photos, total


async def get_photo_by_id(photo_id: int, db: AsyncSession) -> Photo | None:
    """Get a single photo by ID with its tags.

    Args:
        photo_id: The photo's database ID.
        db: Async database session.

    Returns:
        Photo model or None if not found.
    """
    result = await db.execute(
        select(Photo).options(selectinload(Photo.tags)).where(Photo.id == photo_id)
    )
    return result.scalar_one_or_none()


async def delete_photo(photo_id: int, db: AsyncSession) -> bool:
    """Delete a photo and its associated file.

    Args:
        photo_id: The photo's database ID.
        db: Async database session.

    Returns:
        True if deleted, False if not found.
    """
    photo = await get_photo_by_id(photo_id, db)
    if not photo:
        return False

    # Delete file from disk
    filepath = Path(photo.filepath)
    if filepath.exists():
        filepath.unlink()

    await db.delete(photo)
    await db.commit()
    return True


async def get_available_tags(db: AsyncSession) -> dict[str, list[dict]]:
    """Get all unique tags grouped by category.

    Args:
        db: Async database session.

    Returns:
        Dict mapping category names to lists of unique tag values with counts.
    """
    result = await db.execute(
        select(Tag.category, Tag.value, func.count(Tag.id).label("count"))
        .group_by(Tag.category, Tag.value)
        .order_by(Tag.category, func.count(Tag.id).desc())
    )

    grouped: dict[str, list[dict]] = {}
    for row in result:
        category = row.category.value if isinstance(row.category, TagCategory) else row.category
        if category not in grouped:
            grouped[category] = []
        grouped[category].append({
            "value": row.value,
            "count": row.count,
        })

    return grouped
