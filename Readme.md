# Fixed Asset API

A FastAPI-based REST API for managing fixed assets.

## Requirements

- Python 3.12+
- Poetry (dependency manager)

## Setup

### 1. Install dependencies

```bash
poetry install
```

This will create a virtual environment and install all required packages.

### 2. Run the development server

```bash
poetry run uvicorn main:app --reload
```

The server will start at `http://127.0.0.1:8000` with auto-reload enabled.

### 3. Access the API

- **Health check**: `GET http://127.0.0.1:8000/health`
- **Root endpoint**: `GET http://127.0.0.1:8000/`
- **API documentation**: `http://127.0.0.1:8000/docs` (Swagger UI)
- **Alternative docs**: `http://127.0.0.1:8000/redoc` (ReDoc)

## Project Structure

```
fixed-asset-api/
├── main.py              # FastAPI application entry point
├── pyproject.toml       # Poetry configuration and dependencies
├── poetry.lock          # Locked dependency versions
├── venv/                # Virtual environment (created by Poetry)
├── .gitignore           # Git ignore rules
└── README.md            # This file
```

## Dependencies

- **fastapi**: Web framework for building APIs
- **uvicorn**: ASGI server for running FastAPI
- **pytest**: Testing framework (dev)
- **pytest-asyncio**: Async testing support (dev)

## Development

### Testing

```bash
poetry run pytest
```

### Environment Setup

The project uses Poetry's local virtual environment. To view environment info:

```bash
poetry env info
```

## License

MIT
