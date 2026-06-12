"""Photo, Tag, and FaceEmbedding models."""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TagCategory(str, enum.Enum):
    """Tag category enumeration."""

    WHO = "WHO"
    FACES = "FACES"
    WHAT = "WHAT"
    WHERE = "WHERE"


class Photo(Base):
    """Photo model representing an uploaded image."""

    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    filepath: Mapped[str] = mapped_column(String(500), nullable=False)
    upload_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    analyzed: Mapped[bool] = mapped_column(Boolean, default=False)
    analysis_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    tags: Mapped[list["Tag"]] = relationship("Tag", back_populates="photo", cascade="all, delete-orphan")
    face_embeddings: Mapped[list["FaceEmbedding"]] = relationship(
        "FaceEmbedding", back_populates="photo", cascade="all, delete-orphan"
    )


class Tag(Base):
    """Tag model representing a detected feature in a photo."""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    photo_id: Mapped[int] = mapped_column(Integer, ForeignKey("photos.id"), nullable=False)
    category: Mapped[TagCategory] = mapped_column(Enum(TagCategory), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    bounding_box: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string

    photo: Mapped["Photo"] = relationship("Photo", back_populates="tags")
    face_embedding: Mapped["FaceEmbedding | None"] = relationship(
        "FaceEmbedding", back_populates="tag", uselist=False
    )


class FaceEmbedding(Base):
    """Face embedding model for face clustering."""

    __tablename__ = "face_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    photo_id: Mapped[int] = mapped_column(Integer, ForeignKey("photos.id"), nullable=False)
    tag_id: Mapped[int] = mapped_column(Integer, ForeignKey("tags.id"), nullable=False)
    embedding_vector: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    cluster_label: Mapped[str | None] = mapped_column(String(100), nullable=True)

    photo: Mapped["Photo"] = relationship("Photo", back_populates="face_embeddings")
    tag: Mapped["Tag"] = relationship("Tag", back_populates="face_embedding")
