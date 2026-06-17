from pydantic import BaseModel, Field, field_validator


class ContextPreviewRequest(BaseModel):
    """Request body for read-only repository context previews."""

    root_path: str = Field(min_length=1)
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    max_preview_chars: int = Field(default=500, ge=50, le=2000)

    @field_validator("root_path", "query")
    @classmethod
    def text_fields_must_not_be_blank(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("value must not be empty")
        return cleaned_value


class ContextChunkPreview(BaseModel):
    """Bounded preview of one retrieved code chunk."""

    path: str
    language: str | None
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    score: float = Field(ge=0)
    matched_terms: list[str]
    preview: str


class ContextPreviewResponse(BaseModel):
    """Safe API response for repository context previews."""

    root_name: str
    scanned_file_count: int = Field(ge=0)
    skipped_file_count: int = Field(ge=0)
    total_chunks: int = Field(ge=0)
    retrieved_count: int = Field(ge=0)
    chunks: list[ContextChunkPreview]
