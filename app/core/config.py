import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Roasis Backend API"
    app_version: str = "1.0.0"
    app_description: str = "A FastAPI application for Roasis blockchain project"

    # Pinata
    pinata_jwt: str = os.getenv("PINATA_JWT", "")
    pinata_gateway: str = "https://gateway.pinata.cloud/ipfs"

    platform_seed: str = os.getenv("PLATFORM_SEED", "")

    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql://roasis:roasispassword@localhost:5432/roasis_db"
    )
    node_env: str = os.getenv("NODE_ENV", "development")

    # Security
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here")

    class Config:
        env_file = ".env"


settings = Settings()
