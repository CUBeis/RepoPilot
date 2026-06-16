from pydantic import BaseModel, Field


class ScannedFile(BaseModel):
    """Metadata for one scanned text file."""

    path: str
    language: str | None
    extension: str
    size_bytes: int = Field(ge=0)
    line_count: int = Field(ge=0)
    sha256: str


class RepositoryScanResult(BaseModel):
    """Summary and file metadata for a repository scan."""

    root_name: str
    file_count: int = Field(ge=0)
    total_size_bytes: int = Field(ge=0)
    files: list[ScannedFile]
    skipped_count: int = Field(ge=0)
