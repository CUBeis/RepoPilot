from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    """One ordered step in an implementation plan."""

    order: int = Field(ge=1)
    description: str
    target_files: list[str]


class ImplementationPlan(BaseModel):
    """Structured implementation plan for a user issue."""

    objective: str
    relevant_files: list[str]
    steps: list[PlanStep]
    risks: list[str]
    assumptions: list[str]
    confidence: float = Field(ge=0, le=1)
