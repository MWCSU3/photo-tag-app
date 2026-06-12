"""Tests for API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test the health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_upload_photo(client: AsyncClient, sample_image: bytes):
    """Test uploading a photo and receiving analysis results."""
    response = await client.post(
        "/api/photos/upload",
        files={"file": ("test_photo.jpg", sample_image, "image/jpeg")},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["original_filename"] == "test_photo.jpg"
    assert data["analyzed"] is True
    assert data["file_size"] == len(sample_image)
    assert len(data["tags"]) > 0

    # Verify tag categories are present
    categories = {tag["category"] for tag in data["tags"]}
    assert "WHAT" in categories
    assert "WHERE" in categories


@pytest.mark.asyncio
async def test_upload_invalid_extension(client: AsyncClient):
    """Test that uploading a file with invalid extension is rejected."""
    response = await client.post(
        "/api/photos/upload",
        files={"file": ("test.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400
    assert "not allowed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_photos_empty(client: AsyncClient):
    """Test listing photos when none exist."""
    response = await client.get("/api/photos")
    assert response.status_code == 200
    data = response.json()

    assert data["photos"] == []
    assert data["total"] == 0
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_photos_after_upload(client: AsyncClient, sample_image: bytes):
    """Test listing photos after uploading one."""
    # Upload a photo first
    await client.post(
        "/api/photos/upload",
        files={"file": ("test_photo.jpg", sample_image, "image/jpeg")},
    )

    response = await client.get("/api/photos")
    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert len(data["photos"]) == 1
    assert data["photos"][0]["original_filename"] == "test_photo.jpg"


@pytest.mark.asyncio
async def test_list_photos_with_filter(client: AsyncClient, sample_image: bytes):
    """Test filtering photos by tag category."""
    # Upload a photo first
    await client.post(
        "/api/photos/upload",
        files={"file": ("test_photo.jpg", sample_image, "image/jpeg")},
    )

    # Filter by WHAT category
    import json
    categories = json.dumps({"WHAT": ["person"]})
    response = await client.get(f"/api/photos?categories={categories}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_get_photo_by_id(client: AsyncClient, sample_image: bytes):
    """Test getting a single photo by ID."""
    # Upload a photo first
    upload_resp = await client.post(
        "/api/photos/upload",
        files={"file": ("test_photo.jpg", sample_image, "image/jpeg")},
    )
    photo_id = upload_resp.json()["id"]

    response = await client.get(f"/api/photos/{photo_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == photo_id
    assert data["original_filename"] == "test_photo.jpg"


@pytest.mark.asyncio
async def test_get_photo_not_found(client: AsyncClient):
    """Test getting a non-existent photo."""
    response = await client.get("/api/photos/9999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_photo(client: AsyncClient, sample_image: bytes):
    """Test deleting a photo."""
    # Upload a photo first
    upload_resp = await client.post(
        "/api/photos/upload",
        files={"file": ("test_photo.jpg", sample_image, "image/jpeg")},
    )
    photo_id = upload_resp.json()["id"]

    # Delete it
    response = await client.delete(f"/api/photos/{photo_id}")
    assert response.status_code == 200

    # Verify it's gone
    response = await client.get(f"/api/photos/{photo_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_photo_not_found(client: AsyncClient):
    """Test deleting a non-existent photo."""
    response = await client.delete("/api/photos/9999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_tags_empty(client: AsyncClient):
    """Test getting tags when none exist."""
    response = await client.get("/api/tags")
    assert response.status_code == 200
    assert response.json() == {}


@pytest.mark.asyncio
async def test_get_tags_after_upload(client: AsyncClient, sample_image: bytes):
    """Test getting tags after uploading and analyzing a photo."""
    # Upload a photo first
    await client.post(
        "/api/photos/upload",
        files={"file": ("test_photo.jpg", sample_image, "image/jpeg")},
    )

    response = await client.get("/api/tags")
    assert response.status_code == 200
    data = response.json()

    # Should have tags grouped by category
    assert "WHAT" in data
    assert any(tag["value"] == "person" for tag in data["WHAT"])
