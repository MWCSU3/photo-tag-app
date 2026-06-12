"""Pydantic v2 schemas for photos and tags."""

from datetime import datetime

from pydantic import BaseModel, Field


class TagResponse(BaseModel):
    """Response schema for a tag."""

    id: int
    category: str
    value: str
    confidence: float
    bounding_box: str | None = None

    model_config = {"from_attributes": True}


class PhotoCreate(BaseModel):
    """Schema for photo creation (internal use)."""

    filename: str
    original_filename: str
    filepath: str
    file_size: int
    width: int | None = None
    height: int | None = None


class PhotoResponse(BaseModel):
    """Response schema for a single photo with its tags."""

    id: int
    filename: str
    original_filename: str
    upload_date: datetime
    width: int | None = None
    height: int | None = None
    file_size: int
    analyzed: bool
    analysis_date: datetime | None = None
    tags: list[TagResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class PhotoListResponse(BaseModel):
    """Response schema for paginated photo list."""

    photos: list[PhotoResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class FilterParams(BaseModel):
    """Query parameters for filtering photos."""

    categories: dict[str, list[str]] | None = None
    sort_by: str = "upload_date"
    sort_order: str = "desc"
    group_by: str | None = None
    page: int = 1
    page_size: int = 20
