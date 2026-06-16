import pytest

from repopilot.chunking.models import CodeChunk
from repopilot.context.models import RepositoryContext
from repopilot.planning import (
    PlanningError,
    build_planning_prompt,
    create_implementation_plan,
)
from repopilot.planning.prompt import PlanningPromptError
from repopilot.retrieval.models import RetrievedChunk


def make_chunk(
    *,
    path: str,
    text: str,
    chunk_index: int = 0,
    start_line: int = 1,
    end_line: int = 1,
) -> CodeChunk:
    return CodeChunk(
        path=path,
        language="python",
        chunk_index=chunk_index,
        start_line=start_line,
        end_line=end_line,
        text=text,
        sha256="hash",
    )


def make_context(*, retrieved_chunks: list[RetrievedChunk]) -> RepositoryContext:
    return RepositoryContext(
        root_name="sample",
        scanned_file_count=2,
        total_size_bytes=100,
        skipped_file_count=0,
        total_chunks=3,
        retrieved_chunks=retrieved_chunks,
    )


def make_retrieved_chunk(
    *,
    path: str,
    text: str,
    matched_terms: list[str],
    score: float = 3.0,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=make_chunk(path=path, text=text),
        score=score,
        matched_terms=matched_terms,
    )


def test_builds_planning_prompt_containing_issue() -> None:
    context = make_context(retrieved_chunks=[])

    prompt = build_planning_prompt("Fix the login bug", context)

    assert "Fix the login bug" in prompt
    assert "Repository summary:" in prompt


def test_includes_retrieved_chunk_paths_in_prompt() -> None:
    context = make_context(
        retrieved_chunks=[
            make_retrieved_chunk(
                path="src/auth.py",
                text="def login_user(): pass",
                matched_terms=["login"],
            )
        ]
    )

    prompt = build_planning_prompt("Fix login", context)

    assert "src/auth.py" in prompt
    assert "Matched terms: login" in prompt


def test_creates_implementation_plan_from_context() -> None:
    context = make_context(
        retrieved_chunks=[
            make_retrieved_chunk(
                path="src/auth.py",
                text="def login_user(): pass",
                matched_terms=["login", "user"],
            )
        ]
    )

    plan = create_implementation_plan("Fix login bug", context)

    assert plan.objective == "Fix login bug"
    assert plan.relevant_files == ["src/auth.py"]
    assert plan.steps
    assert plan.confidence > 0.5


def test_includes_relevant_files_from_retrieved_chunks() -> None:
    context = make_context(
        retrieved_chunks=[
            make_retrieved_chunk(
                path="src/auth.py",
                text="login",
                matched_terms=["login"],
            ),
            make_retrieved_chunk(
                path="tests/test_auth.py",
                text="login test",
                matched_terms=["login"],
            ),
        ]
    )

    plan = create_implementation_plan("Fix login", context)

    assert plan.relevant_files == ["src/auth.py", "tests/test_auth.py"]


def test_returns_ordered_plan_steps() -> None:
    context = make_context(
        retrieved_chunks=[
            make_retrieved_chunk(
                path="src/auth.py",
                text="login",
                matched_terms=["login"],
            )
        ]
    )

    plan = create_implementation_plan("Fix login", context)

    assert [step.order for step in plan.steps] == [1, 2, 3]


def test_handles_empty_issue_with_clear_error() -> None:
    context = make_context(retrieved_chunks=[])

    with pytest.raises(PlanningError, match="issue must not be empty"):
        create_implementation_plan("   ", context)

    with pytest.raises(PlanningPromptError, match="issue must not be empty"):
        build_planning_prompt("", context)


def test_handles_no_retrieved_chunks_with_low_confidence() -> None:
    context = make_context(retrieved_chunks=[])

    plan = create_implementation_plan("Fix login", context)

    assert plan.relevant_files == []
    assert plan.confidence < 0.5
    assert "more context" in plan.assumptions[0]


def test_is_deterministic_for_same_issue_and_context() -> None:
    context = make_context(
        retrieved_chunks=[
            make_retrieved_chunk(
                path="src/auth.py",
                text="login",
                matched_terms=["login"],
            )
        ]
    )

    first_plan = create_implementation_plan("Fix login", context)
    second_plan = create_implementation_plan("Fix login", context)

    assert first_plan.model_dump() == second_plan.model_dump()


def test_confidence_is_between_zero_and_one() -> None:
    context_with_results = make_context(
        retrieved_chunks=[
            make_retrieved_chunk(
                path="src/auth.py",
                text="login",
                matched_terms=["login"],
            )
        ]
    )
    context_without_results = make_context(retrieved_chunks=[])

    assert 0 <= create_implementation_plan(
        "Fix login", context_with_results
    ).confidence <= 1
    assert 0 <= create_implementation_plan(
        "Fix login", context_without_results
    ).confidence <= 1
