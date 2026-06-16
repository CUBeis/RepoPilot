from collections import defaultdict

from repopilot.context.models import RepositoryContext
from repopilot.planning.models import ImplementationPlan, PlanStep
from repopilot.planning.prompt import PlanningPromptError, build_planning_prompt

LOW_CONTEXT_CONFIDENCE = 0.2
RETRIEVED_CONTEXT_CONFIDENCE = 0.75


class PlanningError(ValueError):
    """Raised when an implementation plan cannot be created."""


def create_implementation_plan(
    issue: str,
    context: RepositoryContext,
) -> ImplementationPlan:
    """Create a deterministic implementation plan from repository context."""
    objective = _normalize_issue(issue)

    if not context.retrieved_chunks:
        return ImplementationPlan(
            objective=objective,
            relevant_files=[],
            steps=[
                PlanStep(
                    order=1,
                    description=(
                        "Gather more repository context before proposing concrete "
                        "file changes."
                    ),
                    target_files=[],
                )
            ],
            risks=[
                "No retrieved chunks matched the issue, so file-level guidance is weak."
            ],
            assumptions=[
                "more context is needed before proposing concrete file changes."
            ],
            confidence=LOW_CONTEXT_CONFIDENCE,
        )

    relevant_files = _unique_relevant_files(context)
    terms_by_file = _matched_terms_by_file(context)
    steps = _build_steps(relevant_files=relevant_files, terms_by_file=terms_by_file)

    return ImplementationPlan(
        objective=objective,
        relevant_files=relevant_files,
        steps=steps,
        risks=[
            (
                "The plan is based on deterministic keyword context, "
                "not semantic analysis."
            ),
            "Implementation details may change after reading full files.",
        ],
        assumptions=[
            "Retrieved chunks contain enough signal to identify likely target files.",
            "No files should be edited until a future implementation layer is added.",
        ],
        confidence=RETRIEVED_CONTEXT_CONFIDENCE,
    )


def build_prompt_for_plan(issue: str, context: RepositoryContext) -> str:
    """Build the prompt used as planning input."""
    try:
        return build_planning_prompt(issue, context)
    except PlanningPromptError as error:
        raise PlanningError(str(error)) from error


def _normalize_issue(issue: str) -> str:
    normalized_issue = issue.strip()
    if not normalized_issue:
        raise PlanningError("issue must not be empty")
    return normalized_issue


def _unique_relevant_files(context: RepositoryContext) -> list[str]:
    relevant_files: list[str] = []
    seen_paths: set[str] = set()
    for result in context.retrieved_chunks:
        path = result.chunk.path
        if path not in seen_paths:
            seen_paths.add(path)
            relevant_files.append(path)
    return relevant_files


def _matched_terms_by_file(context: RepositoryContext) -> dict[str, list[str]]:
    terms_by_file: dict[str, set[str]] = defaultdict(set)
    for result in context.retrieved_chunks:
        terms_by_file[result.chunk.path].update(result.matched_terms)
    return {
        path: sorted(terms)
        for path, terms in sorted(terms_by_file.items(), key=lambda item: item[0])
    }


def _build_steps(
    *,
    relevant_files: list[str],
    terms_by_file: dict[str, list[str]],
) -> list[PlanStep]:
    steps = [
        PlanStep(
            order=1,
            description="Review the retrieved chunks and confirm the issue scope.",
            target_files=relevant_files,
        )
    ]

    for path in relevant_files:
        matched_terms = terms_by_file.get(path, [])
        term_summary = ", ".join(matched_terms) if matched_terms else "retrieved terms"
        steps.append(
            PlanStep(
                order=len(steps) + 1,
                description=(
                    f"Inspect {path} around matched terms: {term_summary}."
                ),
                target_files=[path],
            )
        )

    steps.append(
        PlanStep(
            order=len(steps) + 1,
            description=(
                "Draft the minimal code and test changes needed before any file "
                "editing is attempted."
            ),
            target_files=relevant_files,
        )
    )
    return steps
