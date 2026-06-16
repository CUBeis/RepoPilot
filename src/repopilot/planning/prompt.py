from repopilot.context.models import RepositoryContext


class PlanningPromptError(ValueError):
    """Raised when a planning prompt cannot be built."""


def build_planning_prompt(issue: str, context: RepositoryContext) -> str:
    """Build a deterministic prompt for future planning LLMs."""
    normalized_issue = _normalize_issue(issue)
    lines = [
        "You are RepoPilot, an agentic AI software engineer.",
        "Create a careful implementation plan without editing files.",
        "",
        "User issue:",
        normalized_issue,
        "",
        "Repository summary:",
        f"- Root name: {context.root_name}",
        f"- Scanned files: {context.scanned_file_count}",
        f"- Total chunks: {context.total_chunks}",
        f"- Retrieved chunks: {len(context.retrieved_chunks)}",
        "",
        "Retrieved context:",
    ]

    if not context.retrieved_chunks:
        lines.append("- No retrieved chunks were found.")
        return "\n".join(lines)

    for result in context.retrieved_chunks:
        chunk = result.chunk
        matched_terms = ", ".join(result.matched_terms) or "none"
        lines.extend(
            [
                f"- Path: {chunk.path}",
                f"  Lines: {chunk.start_line}-{chunk.end_line}",
                f"  Score: {result.score}",
                f"  Matched terms: {matched_terms}",
                "  Text:",
                _indent_text(chunk.text, prefix="    "),
            ]
        )

    return "\n".join(lines)


def _normalize_issue(issue: str) -> str:
    normalized_issue = issue.strip()
    if not normalized_issue:
        raise PlanningPromptError("issue must not be empty")
    return normalized_issue


def _indent_text(text: str, *, prefix: str) -> str:
    if text == "":
        return f"{prefix}<empty>"
    return "\n".join(f"{prefix}{line}" for line in text.splitlines())
