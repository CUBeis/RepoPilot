from __future__ import annotations

import argparse
from collections.abc import Sequence

from repopilot.patching.models import (
    PatchAppliedFile,
    PatchApplyResult,
    PatchProposal,
    ProposedFileChange,
)
from repopilot.planning.models import ImplementationPlan, PlanStep
from repopilot.reporting import AgentRunReport, create_agent_run_report
from repopilot.tools.models import CommandResult
from repopilot.validation.models import PatchValidationResult, ValidationCheck


def main(argv: Sequence[str] | None = None) -> int:
    """Run the RepoPilot command-line interface."""

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "report-demo":
        report = _build_report_demo()
        print(report.markdown_summary)
        return 0

    parser.error("unknown command")
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repopilot",
        description="RepoPilot command-line tools.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "report-demo",
        help="Print an in-memory sample AgentRunReport markdown summary.",
    )
    return parser


def _build_report_demo() -> AgentRunReport:
    issue = "Fix login flow validation"
    plan = ImplementationPlan(
        objective="Fix login flow validation",
        relevant_files=["src/auth.py", "tests/test_auth.py"],
        steps=[
            PlanStep(
                order=1,
                description="Inspect the login behavior and validation test.",
                target_files=["src/auth.py", "tests/test_auth.py"],
            )
        ],
        risks=["Authentication behavior may affect existing users."],
        assumptions=["The retrieved login files are sufficient for the fix."],
        confidence=0.82,
    )
    proposal = PatchProposal(
        summary="Update login validation to return the expected boolean result.",
        target_files=["src/auth.py"],
        changes=[
            ProposedFileChange(
                path="src/auth.py",
                reason="Return a boolean success value for login validation.",
                start_line=10,
                end_line=12,
                original_content=(
                    "def login_user(credentials):\n"
                    "    return 'ok' if credentials else 'error'\n"
                ),
                proposed_content=(
                    "def login_user(credentials):\n"
                    "    return bool(credentials)\n"
                ),
            )
        ],
        risks=["Callers may rely on the old string return values."],
        requires_approval=True,
    )
    validation_result = PatchValidationResult(
        apply_result=PatchApplyResult(
            applied_files=[
                PatchAppliedFile(
                    path="src/auth.py",
                    old_content=proposal.changes[0].original_content,
                    new_content=proposal.changes[0].proposed_content,
                    changed=True,
                )
            ],
            changed_file_count=1,
        ),
        checks=[
            ValidationCheck(
                name="pytest",
                command=["pytest"],
                result=CommandResult(
                    command=["pytest"],
                    return_code=0,
                    stdout="1 passed",
                    stderr="",
                    timed_out=False,
                ),
                passed=True,
            )
        ],
        passed=True,
    )

    return create_agent_run_report(
        issue=issue,
        plan=plan,
        patch_proposal=proposal,
        validation_result=validation_result,
    )
