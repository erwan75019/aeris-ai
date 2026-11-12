from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1 import router as api_v1_router
from backend.app.config import get_settings


def create_app() -> FastAPI:
    """Build the ASGI application without performing network I/O."""

    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        description=(
            "Experimental airspace analytics platform. Not certified for navigation, "
            "air-traffic control, or safety-critical use."
        ),
        version=settings.app_version,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    application.include_router(api_v1_router)
    return application


app = create_app()


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "AERIS AI",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}
