from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from repopilot.reporting import create_sample_agent_run_report
from repopilot.schemas.reporting import ReportDemoResponse

router = APIRouter(tags=["reporting"])


@router.get("/report-demo", response_model=ReportDemoResponse)
def get_report_demo() -> ReportDemoResponse:
    """Return a deterministic in-memory sample run report."""

    return ReportDemoResponse.model_validate(
        create_sample_agent_run_report().model_dump()
    )


@router.get("/report-demo/markdown", response_class=PlainTextResponse)
def get_report_demo_markdown() -> str:
    """Return a deterministic in-memory sample run report as Markdown."""

    return create_sample_agent_run_report().markdown_summary
