from __future__ import annotations

import argparse
from collections.abc import Sequence

from repopilot.reporting import create_sample_agent_run_report


def main(argv: Sequence[str] | None = None) -> int:
    """Run the RepoPilot command-line interface."""

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "report-demo":
        report = create_sample_agent_run_report()
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
