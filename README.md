# Roasis Backend API

A FastAPI application for Roasis blockchain project.

## Requirements

- Python 3.8+
- uv package manager

## Installation

1. Install uv (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Install dependencies:
```bash
uv sync
```

## Running the Application

Start the development server:
```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive API docs**: http://localhost:8000/docs
- **ReDoc documentation**: http://localhost:8000/redoc

## API Endpoints

### Health Check
- **GET** `/health` - Returns the health status of the API
  ```json
  {
    "status": "healthy"
  }
  ```

## Development

The application uses:
- **FastAPI** - Modern, fast web framework for building APIs
- **Uvicorn** - ASGI server for running the application
- **Pydantic** - Data validation and settings management
- **uv** - Fast Python package installer and resolver

## License

See LICENSE file for details.