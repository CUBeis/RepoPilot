from fastapi import FastAPI

from repopilot.api.analysis import router as analysis_router
from repopilot.api.apply import router as apply_router
from repopilot.api.context import router as context_router
from repopilot.api.demo import router as demo_router
from repopilot.api.health import router as health_router
from repopilot.api.patches import router as patches_router
from repopilot.api.planning import router as planning_router
from repopilot.api.repair_apply import router as repair_apply_router
from repopilot.api.repair_reports import router as repair_reports_router
from repopilot.api.repairs import router as repairs_router
from repopilot.api.reporting import router as reporting_router
from repopilot.api.repositories import router as repositories_router
from repopilot.api.validation import router as validation_router
from repopilot.api.workflow_reports import router as workflow_reports_router
from repopilot.core.config import get_settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.include_router(analysis_router)
    app.include_router(apply_router)
    app.include_router(context_router)
    app.include_router(demo_router)
    app.include_router(health_router)
    app.include_router(patches_router)
    app.include_router(planning_router)
    app.include_router(repair_apply_router)
    app.include_router(repair_reports_router)
    app.include_router(repairs_router)
    app.include_router(repositories_router)
    app.include_router(reporting_router)
    app.include_router(validation_router)
    app.include_router(workflow_reports_router)
    return app


app = create_app()
