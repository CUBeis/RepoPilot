from fastapi import FastAPI

from repopilot.api.context import router as context_router
from repopilot.api.health import router as health_router
from repopilot.api.reporting import router as reporting_router
from repopilot.api.repositories import router as repositories_router
from repopilot.core.config import get_settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.include_router(context_router)
    app.include_router(health_router)
    app.include_router(repositories_router)
    app.include_router(reporting_router)
    return app


app = create_app()
