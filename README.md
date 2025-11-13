# AI Puzzle MVP

Python API for AI Puzzle MVP project.

## Structure

```
ai-puzzle-mvp/
├── api/
│   ├── __init__.py
│   └── main.py
├── requirements.txt
└── README.md
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the API:
```bash
python api/main.py
```

Or using uvicorn directly:
```bash
uvicorn api.main:app --reload
```

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check endpoint

## Development

The API is built with FastAPI and provides a foundation for building Python-based API endpoints.
