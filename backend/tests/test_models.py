"""Tests for database models."""

from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.database import Base
from app.models.photo import FaceEmbedding, Photo, Tag, TagCategory

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session():
    """Create a test database session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_photo(db_session: AsyncSession):
    """Test creating a Photo record."""
    photo = Photo(
        filename="abc123.jpg",
        original_filename="my_photo.jpg",
        filepath="/uploads/abc123.jpg",
        file_size=1024,
        width=800,
        height=600,
        upload_date=datetime.utcnow(),
    )
    db_session.add(photo)
    await db_session.commit()
    await db_session.refresh(photo)

    assert photo.id is not None
    assert photo.filename == "abc123.jpg"
    assert photo.analyzed is False
    assert photo.width == 800
    assert photo.height == 600


@pytest.mark.asyncio
async def test_create_tag(db_session: AsyncSession):
    """Test creating a Tag associated with a Photo."""
    photo = Photo(
        filename="test.jpg",
        original_filename="test.jpg",
        filepath="/uploads/test.jpg",
        file_size=512,
    )
    db_session.add(photo)
    await db_session.commit()
    await db_session.refresh(photo)

    tag = Tag(
        photo_id=photo.id,
        category=TagCategory.WHAT,
        value="cat",
        confidence=0.95,
    )
    db_session.add(tag)
    await db_session.commit()
    await db_session.refresh(tag)

    assert tag.id is not None
    assert tag.photo_id == photo.id
    assert tag.category == TagCategory.WHAT
    assert tag.value == "cat"
    assert tag.confidence == 0.95


@pytest.mark.asyncio
async def test_photo_tag_relationship(db_session: AsyncSession):
    """Test the relationship between Photo and Tag."""
    photo = Photo(
        filename="rel_test.jpg",
        original_filename="rel_test.jpg",
        filepath="/uploads/rel_test.jpg",
        file_size=256,
    )
    db_session.add(photo)
    await db_session.commit()
    await db_session.refresh(photo)

    tag1 = Tag(photo_id=photo.id, category=TagCategory.WHAT, value="dog", confidence=0.9)
    tag2 = Tag(photo_id=photo.id, category=TagCategory.WHERE, value="park", confidence=0.7)
    db_session.add_all([tag1, tag2])
    await db_session.commit()

    # Query with relationship loading
    result = await db_session.execute(
        select(Photo).options(selectinload(Photo.tags)).where(Photo.id == photo.id)
    )
    loaded_photo = result.scalar_one()

    assert len(loaded_photo.tags) == 2
    tag_values = {t.value for t in loaded_photo.tags}
    assert "dog" in tag_values
    assert "park" in tag_values


@pytest.mark.asyncio
async def test_face_embedding(db_session: AsyncSession):
    """Test creating a FaceEmbedding with relationships."""
    photo = Photo(
        filename="face_test.jpg",
        original_filename="face_test.jpg",
        filepath="/uploads/face_test.jpg",
        file_size=2048,
    )
    db_session.add(photo)
    await db_session.commit()
    await db_session.refresh(photo)

    tag = Tag(
        photo_id=photo.id,
        category=TagCategory.FACES,
        value="face_1",
        confidence=0.92,
    )
    db_session.add(tag)
    await db_session.commit()
    await db_session.refresh(tag)

    embedding = FaceEmbedding(
        photo_id=photo.id,
        tag_id=tag.id,
        embedding_vector=b"\x00\x01\x02\x03" * 32,
    )
    db_session.add(embedding)
    await db_session.commit()
    await db_session.refresh(embedding)

    assert embedding.id is not None
    assert embedding.photo_id == photo.id
    assert embedding.tag_id == tag.id
    assert len(embedding.embedding_vector) == 128


@pytest.mark.asyncio
async def test_tag_categories():
    """Test that all tag categories are properly defined."""
    assert TagCategory.WHO == "WHO"
    assert TagCategory.FACES == "FACES"
    assert TagCategory.WHAT == "WHAT"
    assert TagCategory.WHERE == "WHERE"


@pytest.mark.asyncio
async def test_cascade_delete(db_session: AsyncSession):
    """Test that deleting a photo cascades to tags and embeddings."""
    photo = Photo(
        filename="cascade_test.jpg",
        original_filename="cascade_test.jpg",
        filepath="/uploads/cascade_test.jpg",
        file_size=1024,
    )
    db_session.add(photo)
    await db_session.commit()
    await db_session.refresh(photo)

    tag = Tag(photo_id=photo.id, category=TagCategory.WHAT, value="car", confidence=0.88)
    db_session.add(tag)
    await db_session.commit()

    # Delete the photo
    await db_session.delete(photo)
    await db_session.commit()

    # Verify tag is also deleted
    result = await db_session.execute(select(Tag).where(Tag.photo_id == photo.id))
    remaining_tags = result.scalars().all()
    assert len(remaining_tags) == 0
