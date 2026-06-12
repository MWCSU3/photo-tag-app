# Photo Tagger

An ML-powered photo tagging application that automatically analyzes uploaded photos using computer vision models to detect faces, objects, and scenes, then organizes them with a smart filtering system.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                        │
│   Photo Grid  |  Upload Modal  |  Filter Panel  |  Photo Detail │
└──────────────────────────────────┬──────────────────────────────┘
                                   │ HTTP (port 3000 -> proxy -> 8000)
┌──────────────────────────────────┴──────────────────────────────┐
│                      Backend (FastAPI)                           │
│                                                                  │
│  ┌──────────┐  ┌──────────────────┐  ┌────────────────────────┐ │
│  │ REST API │  │  Photo Service   │  │   Static File Server   │ │
│  │ /api/*   │  │  (upload, query) │  │   /uploads/{filename}  │ │
│  └────┬─────┘  └───────┬──────────┘  └────────────────────────┘ │
│       │                 │                                        │
│  ┌────┴─────────────────┴──────────────────────────────────────┐ │
│  │              ML Analysis Pipeline                            │ │
│  │  Face Analyzer  |  Object Analyzer  |  Scene Analyzer       │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              SQLite Database (SQLAlchemy async)              │ │
│  │  Photos  |  Tags  |  Face Embeddings                        │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## Tech Stack

### Backend
- **Python 3.11** with FastAPI for async REST API
- **SQLAlchemy** (async) with SQLite for data persistence
- **Pydantic** for request/response validation
- **Pillow (PIL)** for image processing
- **ML Models** for photo analysis (face detection, object recognition, scene classification)
- **uv** for Python package management

### Frontend
- **Next.js 14** with App Router
- **TypeScript** for type safety
- **Tailwind CSS** for styling
- **React** with component-based architecture
- **pnpm** for Node.js package management

## Setup Instructions

### Prerequisites
- Python 3.11+ (via pyenv recommended)
- Node.js 22+ with pnpm
- uv (Python package manager)

### Backend Setup

```bash
cd backend

# Set Python version (if using pyenv)
pyenv local 3.11.15

# Install dependencies
uv sync

# Run the backend server
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
pnpm install

# Run the development server
pnpm dev
```

## Running in Development

Start both services simultaneously:

**Terminal 1 - Backend:**
```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
pnpm dev
```

The frontend runs on `http://localhost:3000` and proxies API requests to the backend at `http://localhost:8000`.

Open your browser to `http://localhost:3000` to use the application.

## API Endpoints

### Photos

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/photos/upload` | Upload a photo for analysis |
| `GET` | `/api/photos` | List photos with pagination, filtering, and sorting |
| `GET` | `/api/photos/{id}` | Get a single photo with all tags |
| `DELETE` | `/api/photos/{id}` | Delete a photo |

### Tags

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/tags` | Get all tags grouped by category |

### Static Files

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/uploads/{filename}` | Serve uploaded photo files |

### Query Parameters for `GET /api/photos`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number (1-indexed) |
| `page_size` | int | 20 | Items per page (max 100) |
| `sort_by` | string | "upload_date" | Field to sort by |
| `sort_order` | string | "desc" | Sort direction: "asc" or "desc" |
| `categories` | JSON string | null | Filter by tag categories |
| `group_by` | string | null | Group results by field |

### Health Check

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Application health status |

## ML Models

The analysis pipeline consists of three pluggable analyzers:

### Face Analyzer
- Detects faces in uploaded photos
- Generates face embeddings for similarity matching
- Produces tags in the **FACES** and **WHO** categories
- Returns bounding box coordinates and confidence scores

### Object Analyzer
- Identifies objects and entities present in photos
- Uses image classification and object detection models
- Produces tags in the **WHAT** category (e.g., "person", "dog", "car")
- Returns confidence scores for each detected object

### Scene Analyzer
- Classifies the overall scene context of photos
- Identifies locations and environments
- Produces tags in the **WHERE** category (e.g., "park", "beach", "office")
- Returns confidence scores for scene classifications

All analyzers run on CPU with lightweight model variants optimized for fast inference on demo-scale workloads.

## Filter System

The application uses a two-level filtering logic for photo queries:

- **OR within a category**: Selecting multiple values in the same category (e.g., "dog" OR "cat" in WHAT) returns photos matching any of those values
- **AND across categories**: Selecting values in different categories (e.g., "dog" in WHAT AND "park" in WHERE) returns only photos matching both criteria

This approach gives users intuitive control: broaden results by adding tags within a category, or narrow results by adding constraints across categories.

## Running Tests

### Backend Tests

```bash
cd backend
uv run pytest tests/ -v
```

### Frontend Build Verification

```bash
cd frontend
pnpm build
```

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── dependencies.py
│   │   │   └── routes/
│   │   │       ├── photos.py
│   │   │       └── tags.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── models/
│   │   │   └── photo.py
│   │   ├── schemas/
│   │   │   └── photo.py
│   │   └── services/
│   │       ├── analysis/
│   │       │   ├── base.py
│   │       │   ├── face.py
│   │       │   ├── objects.py
│   │       │   ├── pipeline.py
│   │       │   └── scene.py
│   │       └── photo_service.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── fixtures/
│   │   ├── test_api.py
│   │   ├── test_integration.py
│   │   └── test_models.py
│   ├── pyproject.toml
│   └── uv.lock
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   └── lib/
│   │       ├── api.ts
│   │       └── types.ts
│   ├── package.json
│   └── next.config.ts
└── README.md
```
