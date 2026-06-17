from pydantic import BaseModel, Field


class ProposedFileChange(BaseModel):
    """A proposed change for one file range."""

    path: str
    reason: str
    start_line: int = Field(ge=0)
    end_line: int = Field(ge=0)
    original_content: str
    proposed_content: str


class PatchProposal(BaseModel):
    """Structured patch proposal that requires approval before application."""

    summary: str
    target_files: list[str]
    changes: list[ProposedFileChange]
    risks: list[str]
    requires_approval: bool = True
