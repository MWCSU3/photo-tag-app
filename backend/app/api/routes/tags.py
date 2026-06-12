"""Tags API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.services import photo_service

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("")
async def get_tags(
    db: AsyncSession = Depends(get_db),
) -> dict[str, list[dict]]:
    """Get all available tags grouped by category.

    Returns a dictionary where keys are tag categories (WHO, WHAT, WHERE, FACES)
    and values are lists of {value, count} objects.
    """
    return await photo_service.get_available_tags(db)
