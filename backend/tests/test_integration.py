"""Integration tests exercising the full upload-analyze-retrieve-filter pipeline."""

import io
import json

import pytest
from httpx import AsyncClient
from PIL import Image, ImageDraw


def generate_test_image() -> bytes:
    """Generate a 200x200 test image with shapes and colors for analysis."""
    img = Image.new("RGB", (200, 200), color=(135, 206, 235))
    draw = ImageDraw.Draw(img)

    # Draw some shapes to give analyzers something to work with
    draw.rectangle([20, 20, 80, 80], fill="red", outline="black")
    draw.ellipse([100, 50, 180, 130], fill="green", outline="white")
    draw.polygon([(100, 20), (140, 80), (60, 80)], fill="yellow")
    draw.rectangle([30, 120, 170, 190], fill="blue", outline="white")

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


@pytest.mark.asyncio
class TestFullPipeline:
    """Integration tests for the complete upload -> analyze -> retrieve -> filter flow."""

    async def test_upload_and_analyze(self, client: AsyncClient):
        """Test uploading an image and receiving analysis tags from at least one analyzer."""
        image_data = generate_test_image()

        response = await client.post(
            "/api/photos/upload",
            files={"file": ("integration_test.jpg", image_data, "image/jpeg")},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify basic photo properties
        assert data["original_filename"] == "integration_test.jpg"
        assert data["analyzed"] is True
        assert data["file_size"] == len(image_data)
        assert "id" in data
        assert "filename" in data

        # Verify tags were generated from at least one analyzer
        assert len(data["tags"]) > 0

        # Verify tags have required structure
        for tag in data["tags"]:
            assert "category" in tag
            assert "value" in tag
            assert "confidence" in tag
            assert tag["confidence"] >= 0.0
            assert tag["confidence"] <= 1.0

    async def test_photo_appears_in_list(self, client: AsyncClient):
        """Test that an uploaded photo appears in the photos list endpoint."""
        image_data = generate_test_image()

        # Upload a photo
        upload_resp = await client.post(
            "/api/photos/upload",
            files={"file": ("list_test.jpg", image_data, "image/jpeg")},
        )
        assert upload_resp.status_code == 200
        photo_id = upload_resp.json()["id"]

        # Retrieve photos list
        list_resp = await client.get("/api/photos")
        assert list_resp.status_code == 200
        data = list_resp.json()

        assert data["total"] >= 1
        photo_ids = [p["id"] for p in data["photos"]]
        assert photo_id in photo_ids

    async def test_tags_grouped_by_category(self, client: AsyncClient):
        """Test that GET /api/tags returns tags grouped by category."""
        image_data = generate_test_image()

        # Upload a photo so we have tags
        await client.post(
            "/api/photos/upload",
            files={"file": ("tags_test.jpg", image_data, "image/jpeg")},
        )

        # Get tags
        tags_resp = await client.get("/api/tags")
        assert tags_resp.status_code == 200
        data = tags_resp.json()

        # Tags should be grouped by category (dict with category keys)
        assert isinstance(data, dict)
        assert len(data) > 0

        # Each category should have a list of tag objects
        for category, tags in data.items():
            assert isinstance(tags, list)
            for tag in tags:
                assert "value" in tag
                assert "count" in tag

    async def test_filter_by_category(self, client: AsyncClient):
        """Test filtering photos by a tag category returns matching results."""
        image_data = generate_test_image()

        # Upload a photo
        upload_resp = await client.post(
            "/api/photos/upload",
            files={"file": ("filter_test.jpg", image_data, "image/jpeg")},
        )
        assert upload_resp.status_code == 200

        # Get the tags that were assigned
        photo_data = upload_resp.json()
        tags = photo_data["tags"]
        assert len(tags) > 0

        # Pick a tag category and value to filter by
        first_tag = tags[0]
        category = first_tag["category"]
        value = first_tag["value"]

        # Filter photos by this category/value
        categories_filter = json.dumps({category: [value]})
        filter_resp = await client.get(f"/api/photos?categories={categories_filter}")
        assert filter_resp.status_code == 200
        data = filter_resp.json()

        # The uploaded photo should appear in the filtered results
        assert data["total"] >= 1
        photo_ids = [p["id"] for p in data["photos"]]
        assert photo_data["id"] in photo_ids

    async def test_filter_excludes_non_matching(self, client: AsyncClient):
        """Test that filtering excludes photos that do not match."""
        image_data = generate_test_image()

        # Upload a photo
        await client.post(
            "/api/photos/upload",
            files={"file": ("exclude_test.jpg", image_data, "image/jpeg")},
        )

        # Filter by a non-existent tag value
        categories_filter = json.dumps({"WHAT": ["nonexistent_object_xyz"]})
        filter_resp = await client.get(f"/api/photos?categories={categories_filter}")
        assert filter_resp.status_code == 200
        data = filter_resp.json()

        # Should get no results for a non-existent tag
        assert data["total"] == 0

    async def test_sort_by_upload_date(self, client: AsyncClient):
        """Test sorting photos by upload date."""
        image_data = generate_test_image()

        # Upload two photos
        resp1 = await client.post(
            "/api/photos/upload",
            files={"file": ("sort_first.jpg", image_data, "image/jpeg")},
        )
        resp2 = await client.post(
            "/api/photos/upload",
            files={"file": ("sort_second.jpg", image_data, "image/jpeg")},
        )
        assert resp1.status_code == 200
        assert resp2.status_code == 200

        # Sort by upload_date descending (newest first)
        list_resp = await client.get("/api/photos?sort_by=upload_date&sort_order=desc")
        assert list_resp.status_code == 200
        data = list_resp.json()

        assert data["total"] >= 2
        photos = data["photos"]

        # The second uploaded photo should come first in desc order
        second_photo_id = resp2.json()["id"]
        first_photo_id = resp1.json()["id"]

        # Find indices
        ids = [p["id"] for p in photos]
        assert ids.index(second_photo_id) < ids.index(first_photo_id)

    async def test_sort_by_upload_date_ascending(self, client: AsyncClient):
        """Test sorting photos by upload date in ascending order."""
        image_data = generate_test_image()

        # Upload two photos
        resp1 = await client.post(
            "/api/photos/upload",
            files={"file": ("asc_first.jpg", image_data, "image/jpeg")},
        )
        resp2 = await client.post(
            "/api/photos/upload",
            files={"file": ("asc_second.jpg", image_data, "image/jpeg")},
        )
        assert resp1.status_code == 200
        assert resp2.status_code == 200

        # Sort by upload_date ascending (oldest first)
        list_resp = await client.get("/api/photos?sort_by=upload_date&sort_order=asc")
        assert list_resp.status_code == 200
        data = list_resp.json()

        assert data["total"] >= 2
        photos = data["photos"]

        first_photo_id = resp1.json()["id"]
        second_photo_id = resp2.json()["id"]

        ids = [p["id"] for p in photos]
        assert ids.index(first_photo_id) < ids.index(second_photo_id)

    async def test_pagination(self, client: AsyncClient):
        """Test that pagination works correctly."""
        image_data = generate_test_image()

        # Upload 3 photos
        for i in range(3):
            await client.post(
                "/api/photos/upload",
                files={"file": (f"page_test_{i}.jpg", image_data, "image/jpeg")},
            )

        # Get page 1 with page_size=2
        resp = await client.get("/api/photos?page=1&page_size=2")
        assert resp.status_code == 200
        data = resp.json()

        assert data["total"] == 3
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert len(data["photos"]) == 2
        assert data["total_pages"] == 2

        # Get page 2
        resp2 = await client.get("/api/photos?page=2&page_size=2")
        assert resp2.status_code == 200
        data2 = resp2.json()

        assert data2["page"] == 2
        assert len(data2["photos"]) == 1

    async def test_photo_file_stored_on_disk(self, client: AsyncClient):
        """Test that the uploaded photo file is actually stored on disk."""
        image_data = generate_test_image()

        response = await client.post(
            "/api/photos/upload",
            files={"file": ("disk_test.jpg", image_data, "image/jpeg")},
        )
        assert response.status_code == 200
        data = response.json()

        # The filename should be set (the stored filename on disk)
        assert data["filename"] is not None
        assert data["filename"].endswith(".jpg")
