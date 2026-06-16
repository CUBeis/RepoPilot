import pytest

from repopilot.chunking.models import CodeChunk
from repopilot.retrieval.keyword import KeywordRetrievalError, retrieve_keyword_chunks


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


def test_returns_relevant_chunks_for_query() -> None:
    chunks = [
        make_chunk(path="auth/login.py", text="def authenticate_user(): pass"),
        make_chunk(path="billing/invoice.py", text="def create_invoice(): pass"),
    ]

    results = retrieve_keyword_chunks(chunks, "authenticate user")

    assert len(results) == 1
    assert results[0].chunk.path == "auth/login.py"
    assert results[0].matched_terms == ["authenticate", "user"]


def test_ranks_path_matches_higher_than_text_only_matches() -> None:
    chunks = [
        make_chunk(path="docs/readme.py", text="auth"),
        make_chunk(path="auth/routes.py", text="nothing relevant"),
    ]

    results = retrieve_keyword_chunks(chunks, "auth")

    assert [result.chunk.path for result in results] == [
        "auth/routes.py",
        "docs/readme.py",
    ]
    assert results[0].score > results[1].score


def test_is_case_insensitive() -> None:
    chunks = [make_chunk(path="AUTH/routes.py", text="LOGIN handler")]

    results = retrieve_keyword_chunks(chunks, "auth login")

    assert len(results) == 1
    assert results[0].matched_terms == ["auth", "login"]


def test_ignores_simple_punctuation() -> None:
    chunks = [make_chunk(path="auth/routes.py", text="reset-password handler")]

    results = retrieve_keyword_chunks(chunks, "reset, password!")

    assert len(results) == 1
    assert results[0].matched_terms == ["password", "reset"]


def test_returns_top_k_only() -> None:
    chunks = [
        make_chunk(path=f"file_{index}.py", text="query match", chunk_index=index)
        for index in range(5)
    ]

    results = retrieve_keyword_chunks(chunks, "query", top_k=2)

    assert len(results) == 2


def test_returns_empty_list_for_empty_query() -> None:
    chunks = [make_chunk(path="auth/routes.py", text="auth login")]

    assert retrieve_keyword_chunks(chunks, "  ") == []


def test_returns_empty_list_for_empty_chunks() -> None:
    assert retrieve_keyword_chunks([], "auth") == []


def test_includes_matched_terms() -> None:
    chunks = [make_chunk(path="auth/routes.py", text="login user session")]

    results = retrieve_keyword_chunks(chunks, "auth login missing")

    assert results[0].matched_terms == ["auth", "login"]


def test_has_deterministic_ordering_when_scores_tie() -> None:
    chunks = [
        make_chunk(path="b.py", text="shared"),
        make_chunk(path="a.py", text="shared"),
    ]

    first_results = retrieve_keyword_chunks(chunks, "shared")
    second_results = retrieve_keyword_chunks(list(reversed(chunks)), "shared")

    assert [result.chunk.path for result in first_results] == ["a.py", "b.py"]
    assert [result.chunk.path for result in second_results] == ["a.py", "b.py"]


def test_raises_clear_error_for_invalid_top_k() -> None:
    chunks = [make_chunk(path="auth/routes.py", text="auth")]

    with pytest.raises(KeywordRetrievalError, match="top_k"):
        retrieve_keyword_chunks(chunks, "auth", top_k=0)
