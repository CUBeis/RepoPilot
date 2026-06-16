from pydantic import BaseModel, Field

from repopilot.chunking.models import CodeChunk


class RetrievedChunk(BaseModel):
    """A code chunk returned by deterministic retrieval."""

    chunk: CodeChunk
    score: float = Field(ge=0)
    matched_terms: list[str]
