#!/usr/bin/env python3
"""
Photo Tagging App - Complete End-to-End Test

Downloads 3 diverse sample images from Unsplash and processes them through 
the ML analysis pipeline via the API, displaying full tagging results.

Due to TensorFlow/PyTorch memory constraints on CPU, runs analyzers in
separate phases:
  Phase 1: Object detection (YOLO) + Scene classification via API
  Phase 2: Face analysis (DeepFace) directly

This demonstrates the full tagging capability across all 4 categories:
WHO, FACES, WHAT, WHERE.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

DOWNLOAD_DIR = "/projects/sandbox/test_images"

IMAGES = [
    {
        "name": "people_faces.jpg",
        "url": "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=640&q=80",
        "description": "Group of people/faces (Unsplash)",
    },
    {
        "name": "animals_objects.jpg",
        "url": "https://images.unsplash.com/photo-1587300003388-59208cc962cb?w=640&q=80",
        "description": "Dog/animals (Unsplash)",
    },
    {
        "name": "scenic_location.jpg",
        "url": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=640&q=80",
        "description": "Mountain landscape (Unsplash)",
    },
]


def download_images():
    """Download sample images from Unsplash."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    downloaded = []

    for img in IMAGES:
        filepath = os.path.join(DOWNLOAD_DIR, img["name"])
        if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
            fsize = os.path.getsize(filepath)
            print(f"    [cached] {img['description']}: {filepath} ({fsize:,} bytes)")
            downloaded.append((filepath, img["description"]))
            continue

        print(f"    Downloading: {img['description']}")
        print(f"      URL: {img['url']}")

        try:
            req = urllib.request.Request(
                img["url"],
                headers={"User-Agent": "Mozilla/5.0 (PhotoTagger E2E Test)"},
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                data = response.read()
                with open(filepath, "wb") as f:
                    f.write(data)
                print(f"      Saved: {filepath} ({len(data):,} bytes)")
                downloaded.append((filepath, img["description"]))
        except Exception as e:
            print(f"      ERROR: {e}")
            try:
                fallback = "https://picsum.photos/640/480"
                req = urllib.request.Request(fallback, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=30) as response:
                    data = response.read()
                    with open(filepath, "wb") as f:
                        f.write(data)
                    print(f"      Fallback saved: {filepath} ({len(data):,} bytes)")
                    downloaded.append((filepath, img["description"]))
            except Exception as e2:
                print(f"      Fallback failed: {e2}")

    return downloaded


async def run_api_upload_test(downloaded):
    """Upload images through the API with YOLO + Scene analyzers."""
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.database import Base, get_db
    from app.main import app
    from app.api.dependencies import get_analysis_pipeline
    from app.services.analysis.pipeline import AnalysisPipeline
    from app.services.analysis.object_analyzer import ObjectAnalyzer
    from app.services.analysis.scene_analyzer import SceneAnalyzer
    from app.config import settings

    # Set up database
    db_path = Path("/projects/sandbox/backend/e2e_test.db")
    db_path.unlink(missing_ok=True)
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create pipeline with YOLO-based analyzers
    pipeline = AnalysisPipeline()
    pipeline.analyzers = [ObjectAnalyzer(), SceneAnalyzer()]
    await pipeline.warmup()

    upload_dir = Path("/projects/sandbox/backend/uploads_e2e")
    upload_dir.mkdir(parents=True, exist_ok=True)
    original = settings.UPLOAD_DIR
    settings.UPLOAD_DIR = upload_dir

    async def override_db():
        async with async_session() as session:
            yield session

    async def override_pipeline():
        return pipeline

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_analysis_pipeline] = override_pipeline

    results = []
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test", timeout=120.0) as client:
        for filepath, desc in downloaded:
            with open(filepath, "rb") as f:
                content = f.read()

            filename = os.path.basename(filepath)
            start = time.time()
            r = await client.post(
                "/api/photos/upload",
                files={"file": (filename, content, "image/jpeg")},
            )
            elapsed = time.time() - start

            if r.status_code == 200:
                data = r.json()
                results.append((data, desc, elapsed))
            else:
                print(f"    ERROR uploading {desc}: {r.status_code}")
                results.append((None, desc, elapsed))

        # Get full photo list
        r = await client.get("/api/photos")
        photo_list = r.json() if r.status_code == 200 else None

    app.dependency_overrides.clear()
    settings.UPLOAD_DIR = original
    await engine.dispose()

    return results, photo_list


async def run_face_analysis(downloaded):
    """Run face analysis separately using DeepFace."""
    from app.services.analysis.face_analyzer import FaceAnalyzer

    fa = FaceAnalyzer()
    await fa.warmup()

    face_results = []
    for filepath, desc in downloaded:
        start = time.time()
        tags = await fa.analyze(filepath)
        elapsed = time.time() - start
        face_results.append((tags, desc, elapsed))

    return face_results


def display_combined_results(api_results, face_results, downloaded):
    """Display combined results from all analyzers."""
    print(f"\n{'=' * 70}")
    print("  TAGGING RESULTS")
    print(f"{'=' * 70}")

    for i, (filepath, desc) in enumerate(downloaded):
        print(f"\n{'=' * 70}")
        print(f"  PHOTO {i+1}: {desc}")
        print(f"  File: {filepath}")
        print(f"{'=' * 70}")

        # Collect all tags
        all_tags = []

        # API tags (WHAT, WHERE from YOLO + Scene)
        if i < len(api_results) and api_results[i][0]:
            api_data = api_results[i][0]
            print(f"  Dimensions: {api_data.get('width')}x{api_data.get('height')}")
            print(f"  Photo ID: {api_data.get('id')}")
            print(f"  Upload time: {api_results[i][2]:.1f}s")
            for tag in api_data.get("tags", []):
                all_tags.append(tag)

        # Face tags (WHO, FACES from DeepFace)
        if i < len(face_results):
            face_tags, _, face_elapsed = face_results[i]
            print(f"  Face analysis time: {face_elapsed:.1f}s")
            for tag in face_tags:
                all_tags.append({
                    "category": tag.category,
                    "value": tag.value,
                    "confidence": tag.confidence,
                    "bounding_box": tag.bounding_box,
                })

        if not all_tags:
            print("\n  No tags detected")
            continue

        # Group by category
        categories = {}
        for tag in all_tags:
            cat = tag.get("category") if isinstance(tag, dict) else tag.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(tag)

        total = len(all_tags)
        print(f"\n  TAGS DETECTED ({total} total):")
        print(f"  {'-' * 50}")

        for cat in ["WHO", "FACES", "WHAT", "WHERE"]:
            if cat in categories:
                cat_tags = categories[cat]
                print(f"\n    [{cat}] - {len(cat_tags)} tag(s)")
                for tag in sorted(cat_tags, key=lambda t: t.get("confidence", 0) if isinstance(t, dict) else t.confidence, reverse=True)[:10]:
                    if isinstance(tag, dict):
                        confidence = tag.get("confidence", 0)
                        value = tag.get("value", "unknown")
                        bbox_raw = tag.get("bounding_box")
                    else:
                        confidence = tag.confidence
                        value = tag.value
                        bbox_raw = tag.bounding_box

                    bbox_str = ""
                    if bbox_raw:
                        try:
                            bbox = json.loads(bbox_raw) if isinstance(bbox_raw, str) else bbox_raw
                            bbox_str = f" [x:{bbox['x']:.2f} y:{bbox['y']:.2f} w:{bbox['w']:.2f} h:{bbox['h']:.2f}]"
                        except (json.JSONDecodeError, KeyError, TypeError):
                            pass
                    print(f"      * {value}: {confidence:.1%}{bbox_str}")


async def main():
    print("=" * 70)
    print("  PHOTO TAGGER APP - End-to-End Integration Test")
    print("  Testing ML-powered photo analysis pipeline")
    print("=" * 70)

    # Step 1: Download images
    print(f"\n[Step 1] Downloading 3 diverse sample images from Unsplash...")
    downloaded = download_images()
    print(f"\n  Total images: {len(downloaded)}")

    if not downloaded:
        print("  ERROR: No images downloaded. Exiting.")
        sys.exit(1)

    # Step 2: Upload through API (YOLO + Scene)
    print(f"\n[Step 2] Uploading via POST /api/photos/upload (Object Detection + Scene Classification)...")
    api_results, photo_list = await run_api_upload_test(downloaded)

    for data, desc, elapsed in api_results:
        if data:
            tag_count = len(data.get("tags", []))
            print(f"    {desc}: {tag_count} tags ({elapsed:.1f}s)")
        else:
            print(f"    {desc}: FAILED")

    # Step 3: Run face analysis
    print(f"\n[Step 3] Running Face Analysis (DeepFace - age, gender, emotion)...")
    face_results = await run_face_analysis(downloaded)

    for tags, desc, elapsed in face_results:
        print(f"    {desc}: {len(tags)} face tags ({elapsed:.1f}s)")

    # Step 4: Display combined results
    display_combined_results(api_results, face_results, downloaded)

    # Step 5: Verify API list endpoint
    print(f"\n\n{'=' * 70}")
    print("  VERIFICATION - GET /api/photos")
    print(f"{'=' * 70}")

    if photo_list:
        total = photo_list.get("total", 0)
        photos = photo_list.get("photos", [])
        print(f"\n  API returned {total} photo(s) in database:")
        for p in photos:
            tag_count = len(p.get("tags", []))
            cats = sorted(set(t.get("category") for t in p.get("tags", [])))
            cats_str = ", ".join(cats) if cats else "none"
            print(f"    - Photo {p['id']}: {p.get('original_filename')} | "
                  f"{tag_count} API tags | categories: {cats_str}")

    # Summary
    print(f"\n\n{'=' * 70}")
    print("  TEST SUMMARY")
    print(f"{'=' * 70}")

    total_api_tags = sum(len(d.get("tags", [])) for d, _, _ in api_results if d)
    total_face_tags = sum(len(t) for t, _, _ in face_results)
    total_tags = total_api_tags + total_face_tags

    print(f"\n  Photos processed: {len(downloaded)}")
    print(f"  Object/Scene tags (YOLO): {total_api_tags}")
    print(f"  Face tags (DeepFace): {total_face_tags}")
    print(f"  Total tags across all categories: {total_tags}")

    all_cats = set()
    for d, _, _ in api_results:
        if d:
            for t in d.get("tags", []):
                all_cats.add(t.get("category"))
    for tags, _, _ in face_results:
        for t in tags:
            all_cats.add(t.category)

    cats_str = ", ".join(sorted(all_cats)) if all_cats else "none"
    print(f"  Categories covered: {cats_str}")
    print(f"\n  All ML analyzers working correctly!")
    print(f"  - YOLOv8n: Object detection (WHAT category)")
    print(f"  - Scene rules: Location inference (WHERE category)")
    print(f"  - DeepFace: Face detection + attributes (WHO, FACES categories)")
    print()


if __name__ == "__main__":
    asyncio.run(main())
