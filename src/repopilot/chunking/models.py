from pydantic import BaseModel, Field


class CodeChunk(BaseModel):
    """A deterministic line-based chunk of a source file."""

    path: str
    language: str | None
    chunk_index: int = Field(ge=0)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    text: str
    sha256: str
