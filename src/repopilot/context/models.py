from pydantic import BaseModel, Field

from repopilot.retrieval.models import RetrievedChunk


class RepositoryContext(BaseModel):
    """Prepared repository context for a user query."""

    root_name: str
    scanned_file_count: int = Field(ge=0)
    total_size_bytes: int = Field(ge=0)
    skipped_file_count: int = Field(ge=0)
    total_chunks: int = Field(ge=0)
    retrieved_chunks: list[RetrievedChunk]
