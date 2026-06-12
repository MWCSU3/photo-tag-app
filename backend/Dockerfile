# Dockerfile for Photo Tagger Backend
# Python 3.11 FastAPI app with ML models (YOLOv8, DeepFace, Places365, CLIP)

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for OpenCV, image processing, and ML libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Install Python dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY app/ ./app/
COPY static/ ./static/

# Download YOLOv8n model during build (avoids download at runtime)
RUN wget -q https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt -O yolov8n.pt

# Create necessary directories
RUN mkdir -p data uploads model_cache

# Expose default port
EXPOSE 8000

# Run with shell form so PORT env var is expanded at runtime
# Railway injects PORT environment variable
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
