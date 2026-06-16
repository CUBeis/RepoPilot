from pydantic import BaseModel, Field


class FileReadResult(BaseModel):
    """Structured result for a safe read-only file operation."""

    path: str
    start_line: int = Field(ge=0)
    end_line: int = Field(ge=0)
    content: str
    total_lines: int = Field(ge=0)
    size_bytes: int = Field(ge=0)
