from pydantic import BaseModel, Field, field_validator


class RepositoryScanSummaryRequest(BaseModel):
    """Request body for a read-only repository scan summary."""

    root_path: str = Field(min_length=1)

    @field_validator("root_path")
    @classmethod
    def root_path_must_not_be_blank(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("root_path must not be empty")
        return cleaned_value


class ScannedFileSummary(BaseModel):
    """Safe API summary for one scanned file."""

    path: str
    language: str | None
    extension: str
    size_bytes: int = Field(ge=0)
    line_count: int = Field(ge=0)


class RepositoryScanSummaryResponse(BaseModel):
    """Safe API response for a repository scan summary."""

    root_name: str
    file_count: int = Field(ge=0)
    total_size_bytes: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    files: list[ScannedFileSummary]
