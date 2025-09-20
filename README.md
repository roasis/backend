# Roasis Backend API

A FastAPI application for Roasis blockchain project with XRPL wallet authentication.

## Features

- 🚀 **FastAPI** - Modern, fast web framework
- 🔐 **XRPL Wallet Auth** - Signature-based authentication
- 🗄️ **PostgreSQL** - Robust database with SQLAlchemy ORM
- 🐳 **Docker** - Containerized deployment
- 🔒 **Nginx** - Reverse proxy with SSL support
- 📝 **Auto Documentation** - Interactive API docs
- 🧹 **Code Quality** - Pre-commit hooks with linting

## Quick Start with Docker

1. **Clone and start the application:**
```bash
git clone git@github.com:roasis/backend.git
cd backend
docker-compose up
```

2. **Access the application:**
- **API**: http://localhost (via Nginx proxy)
- **Direct API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Development Setup

### Requirements
- Python 3.12+
- uv package manager
- Docker & Docker Compose

### Local Development

1. **Install uv (if not already installed):**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. **Install dependencies:**
```bash
uv sync --dev
```

3. **Set up pre-commit hooks:**
```bash
uv run pre-commit install
```

## API Endpoints

### System
- **GET** `/` - Welcome message
- **GET** `/health` - Health check with database status

## Database

### Running Migrations
```bash
# Create new migration
uv run alembic revision --autogenerate -m "Description"

# Apply migrations
uv run alembic upgrade head

# Rollback migration
uv run alembic downgrade -1
```

## Code Quality

### Pre-commit Hooks
Automatically run on every commit:
- **Black** - Code formatting
- **isort** - Import sorting
- **flake8** - Linting
- **mypy** - Type checking

### Manual Code Quality Checks
```bash
# Format code
uv run black .
uv run isort .

# Lint code
uv run flake8 .
uv run mypy .

# Run all pre-commit hooks
uv run pre-commit run --all-files
```

## Docker Deployment

### Production Deployment
```bash
# Deploy with Nginx, PostgreSQL, and SSL
./deploy.sh
```

### Development with Docker
```bash
# Start all services
docker-compose up

# Start specific service
docker-compose up postgres

# View logs
docker-compose logs -f backend
```

### Environment Variables
Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
# Edit .env with your settings
```

## Technology Stack

- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - SQL toolkit and ORM
- **PostgreSQL** - Relational database
- **Alembic** - Database migration tool
- **XRPL-py** - XRP Ledger Python library
- **PyJWT** - JSON Web Token implementation
- **Pydantic** - Data validation using Python type hints
- **Docker** - Containerization
- **Nginx** - Web server and reverse proxy
- **uv** - Fast Python package manager

## Contributing

1. **Fork the repository**
2. **Create a feature branch:** `git checkout -b feature/amazing-feature`
3. **Install dev dependencies:** `uv sync --dev`
4. **Set up pre-commit:** `uv run pre-commit install`
5. **Make your changes**
6. **Run tests:** `uv run pytest`
7. **Commit your changes:** `git commit -m 'Add amazing feature'`
8. **Push to the branch:** `git push origin feature/amazing-feature`
9. **Open a Pull Request**

## License

See LICENSE file for details.
