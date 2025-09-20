from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Import models for table creation
from app.core import models  # noqa: F401
from app.core.config import settings
from app.domains.artist.router import router as artist_router
from app.domains.artwork.router import router as artwork_router
from app.domains.auth.router import router as auth_router
from app.domains.gallery.router import router as gallery_router
from app.domains.nfts.router import router as nfts_router
from app.shared.database.connection import Base, engine, get_db

# Create database tables
Base.metadata.create_all(bind=engine)


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
    )

    # Add CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://roasis-front.vercel.app",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    application.include_router(auth_router, prefix="/api/v1")
    application.include_router(artist_router, prefix="/api/v1")
    application.include_router(artwork_router, prefix="/api/v1")
    application.include_router(gallery_router, prefix="/api/v1")
    application.include_router(nfts_router, prefix="/api/v1")

    @application.get("/")
    async def root() -> dict[str, str]:
        return {"message": "Welcome to Roasis"}

    @application.get("/health")
    async def health_check(db: Session = Depends(get_db)) -> dict[str, str]:
        try:
            # Test database connection
            db.execute("SELECT 1")
            return {
                "status": "healthy",
                "database": "connected",
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
            }

    return application


app = create_app()
