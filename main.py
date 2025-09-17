from fastapi import FastAPI

def create_app() -> FastAPI:
    app = FastAPI(
        title="Roasis Backend API",
        description="A FastAPI application for Roasis blockchain project",
        version="1.0.0"
    )

    @app.get("/")
    async def root():
        return {"message": "Welcome to Roasis"}

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return app

app = create_app()