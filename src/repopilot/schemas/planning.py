from pydantic import BaseModel, Field, field_validator


class PlanningPreviewRequest(BaseModel):
    """Request body for read-only deterministic planning previews."""

    root_path: str = Field(min_length=1)
    issue: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)

    @field_validator("root_path", "issue")
    @classmethod
    def text_fields_must_not_be_blank(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("value must not be empty")
        return cleaned_value


class PlanStepResponse(BaseModel):
    """One ordered deterministic plan step returned by the API."""

    order: int = Field(ge=1)
    description: str
    target_files: list[str]


class ImplementationPlanResponse(BaseModel):
    """Safe API representation of an implementation plan."""

    objective: str
    relevant_files: list[str]
    steps: list[PlanStepResponse]
    risks: list[str]
    assumptions: list[str]
    confidence: float = Field(ge=0, le=1)


class PlanningPreviewResponse(BaseModel):
    """Safe API response for deterministic planning previews."""

    root_name: str
    issue: str
    scanned_file_count: int = Field(ge=0)
    skipped_file_count: int = Field(ge=0)
    total_chunks: int = Field(ge=0)
    retrieved_count: int = Field(ge=0)
    plan: ImplementationPlanResponse
