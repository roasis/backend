import os
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.shared.database.connection import engine, get_db, Base
from app.domains.users.router import router as users_router
# from app.domains.blockchain.router import router as blockchain_router

# Import models for table creation
import app.core.models

# Create database tables
Base.metadata.create_all(bind=engine)

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version
    )

    # Include routers
    app.include_router(users_router, prefix="/api/v1/users")

    @app.get("/")
    async def root():
        return {"message": "Welcome to Roasis"}

    @app.get("/health")
    async def health_check(db: Session = Depends(get_db)):
        try:
            # Test database connection
            db.execute("SELECT 1")
            return {
                "status": "healthy",
                "environment": settings.node_env,
                "database": "connected"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "environment": settings.node_env,
                "database": "disconnected",
                "error": str(e)
            }

    return app

app = create_app()