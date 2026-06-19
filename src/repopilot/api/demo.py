from fastapi import APIRouter

from repopilot.api.workflow_reports import build_workflow_report
from repopilot.schemas.workflow_reports import (
    WorkflowReportRequest,
    WorkflowReportResponse,
)

router = APIRouter(tags=["demo"])


@router.get("/demo/workflow", response_model=WorkflowReportResponse)
def get_demo_workflow_report() -> WorkflowReportResponse:
    """Return a deterministic in-memory successful workflow report."""

    return build_workflow_report(_demo_workflow_request())


def _demo_workflow_request() -> WorkflowReportRequest:
    return WorkflowReportRequest.model_validate(
        {
            "issue": "Fix login success handling",
            "plan": {
                "objective": "Fix login success handling",
                "relevant_files": ["src/auth.py", "tests/test_auth.py"],
                "steps": [
                    {
                        "order": 1,
                        "description": "Inspect login return behavior.",
                        "target_files": ["src/auth.py"],
                    },
                    {
                        "order": 2,
                        "description": "Confirm the login test covers success.",
                        "target_files": ["tests/test_auth.py"],
                    },
                ],
                "risks": ["May affect authentication behavior."],
                "assumptions": ["The retrieved auth context is relevant."],
                "confidence": 0.86,
            },
            "patch_proposal": {
                "summary": "Return a boolean success value from login.",
                "target_files": ["src/auth.py"],
                "changes": [
                    {
                        "path": "src/auth.py",
                        "reason": "Make login return the expected boolean.",
                        "start_line": 10,
                        "end_line": 12,
                        "original_preview": "def login_user(...): ...",
                        "proposed_preview": "def login_user(...): return True",
                    }
                ],
                "risks": ["May affect callers that expect the old value."],
                "requires_approval": True,
            },
            "apply_result": {
                "changed_file_count": 1,
                "applied_files": [
                    {"path": "src/auth.py", "changed": True},
                ],
                "validation": None,
            },
            "validation_result": {
                "changed_file_count": 1,
                "applied_files": [
                    {"path": "src/auth.py", "changed": True},
                ],
                "checks": [
                    {
                        "name": "pytest",
                        "command": ["pytest"],
                        "return_code": 0,
                        "timed_out": False,
                        "stdout_preview": "demo tests passed",
                        "stderr_preview": "",
                        "passed": True,
                    },
                    {
                        "name": "ruff check .",
                        "command": ["ruff", "check", "."],
                        "return_code": 0,
                        "timed_out": False,
                        "stdout_preview": "demo lint passed",
                        "stderr_preview": "",
                        "passed": True,
                    },
                ],
                "passed": True,
            },
            "failure_analysis": None,
            "repair_approval": None,
            "repair_apply_report": None,
        }
    )
