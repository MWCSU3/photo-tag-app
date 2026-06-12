"""Application configuration using pydantic-settings."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    DATABASE_URL: str = "sqlite+aiosqlite:///./data/photos.db"
    UPLOAD_DIR: Path = Path("./uploads")
    MODEL_CACHE_DIR: Path = Path("./model_cache")
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}

    model_config = {"env_prefix": "APP_", "env_file": ".env"}


settings = Settings()
